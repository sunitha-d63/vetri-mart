from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
import re
from .models import Order, DeliveryZone,Product
from .models import ContactMessage,CustomUser
from django.core.validators import RegexValidator
from .models import Order, DeliveryZone
from .choices import SLOT_CHOICES
from django.contrib.auth import authenticate

User = get_user_model()
CustomUser = get_user_model()

from django.db import IntegrityError, transaction

CustomUser = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Username',
            'class': 'form-control',
            'autocomplete': 'username'
        }),
        help_text="Username can only contain letters, numbers, underscores, and periods (no spaces)."
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Email',
            'class': 'form-control',
            'autocomplete': 'email'
        })
    )

    phone = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Phone Number',
            'class': 'form-control',
            'autocomplete': 'tel'
        }),
        help_text="Enter a valid 10-digit mobile number starting with 6–9."
    )

    role = forms.ChoiceField(
        choices=CustomUser.ROLE_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password',
            'class': 'form-control',
            'autocomplete': 'new-password'
        }),
        help_text="Password must be at least 8 characters, include uppercase, lowercase, and a number."
    )

    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm Password',
            'class': 'form-control',
            'autocomplete': 'new-password'
        })
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phone', 'role', 'password1', 'password2']

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not re.match(r'^[A-Za-z0-9](?:[A-Za-z0-9._]*[A-Za-z0-9])?$', username):
            raise ValidationError(
                "Username can only contain letters, numbers, underscores (_), and periods (.). "
                "It cannot start/end with a special character or contain spaces."
            )
        if len(username) < 3 or len(username) > 30:
            raise ValidationError("Username must be between 3 and 30 characters long.")
        # Normalize for uniqueness check (case-insensitive)
        if CustomUser.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken. Please choose another.")
        # Optionally store normalized:
        return username.lower()  # NOTE: storing username lowercase prevents case issues

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise ValidationError("This email address is already registered.")
        return email.lower()

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not re.match(r'^[6-9]\d{9}$', phone):
            raise ValidationError("Enter a valid 10-digit Indian mobile number starting with 6–9.")
        if CustomUser.objects.filter(phone=phone).exists():
            raise ValidationError("This phone number is already registered.")
        return phone

    def clean_password1(self):
        password = self.cleaned_data.get('password1', '')
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        if not re.search(r'[A-Z]', password):
            raise ValidationError("Password must contain at least one uppercase letter.")
        if not re.search(r'[a-z]', password):
            raise ValidationError("Password must contain at least one lowercase letter.")
        if not re.search(r'[0-9]', password):
            raise ValidationError("Password must contain at least one number.")
        if re.search(r'\s', password):
            raise ValidationError("Password cannot contain spaces.")
        return password

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        """
        Override save to ensure password is hashed and username/email normalized.
        Use transaction to minimize partial writes. Return user instance.
        """
        user = super(UserCreationForm, self).save(commit=False)
        username = (self.cleaned_data.get('username') or '').lower()
        email = (self.cleaned_data.get('email') or '').lower()
        phone = self.cleaned_data.get('phone')
        role = self.cleaned_data.get('role')

        user.username = username
        user.email = email
        user.phone = phone
        user.role = role
        user.set_password(self.cleaned_data["password1"])

        if commit:
            try:
                with transaction.atomic():
                    user.save()
            except IntegrityError:
                # If a race-condition caused duplicate, raise user-friendly error
                raise ValidationError("Unable to create account. Please try again with different credentials.")
        else:
            # caller will save later
            pass

        return user

CustomUser = get_user_model()

class UserLoginForm(forms.Form):
    identifier = forms.CharField(   # username or email
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username or Email'}),
        required=True
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
        required=True
    )

    def clean(self):
        cleaned_data = super().clean()
        identifier = cleaned_data.get('identifier', '').strip()
        password = cleaned_data.get('password')

        if not identifier or not password:
            raise ValidationError("Please provide both identifier and password.")

        # Try to find user by username (case-insensitive) or email (case-insensitive)
        user_qs = CustomUser.objects.filter(username__iexact=identifier)
        if not user_qs.exists():
            user_qs = CustomUser.objects.filter(email__iexact=identifier)

        if not user_qs.exists():
            raise ValidationError("Invalid username/email or password.")

        user_obj = user_qs.first()

        # authenticate using the actual username stored in DB
        user = authenticate(username=user_obj.username, password=password)
        if user is None:
            raise ValidationError("Invalid username/email or password.")

        # Optionally check is_active
        if not user.is_active:
            raise ValidationError("This account is inactive. Contact support.")

        cleaned_data['user'] = user
        return cleaned_data

    def get_user(self):
        return self.cleaned_data.get('user')



class AddToCartForm(forms.Form):
    weight = forms.CharField(required=True)
    quantity = forms.IntegerField(min_value=1, initial=1)

name_validator = RegexValidator(
    r'^[A-Za-z\s]{3,50}$',
    "Full name must contain only letters and spaces (3–50 chars)."
)
phone_validator = RegexValidator(
    r'^[6-9]\d{9}$',
    "Enter a valid 10-digit Indian mobile number."
)
pincode_validator = RegexValidator(
    r'^\d{6}$',
    "Enter a valid 6-digit pincode."
)

class OrderForm(forms.ModelForm):

    delivery_zone = forms.ModelChoiceField(
        queryset=DeliveryZone.objects.filter(is_active=True).order_by('area_name'),
        required=False,
        label="Select Delivery Area / Pincode",
        empty_label="Choose your delivery area"
    )

    delivery_slot = forms.ChoiceField(
        choices=SLOT_CHOICES,
        required=True,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    latitude = forms.FloatField(widget=forms.HiddenInput(), required=False)
    longitude = forms.FloatField(widget=forms.HiddenInput(), required=False)
    address_from_map = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Order
        fields = [
            'full_name', 'email', 'phone',
            'street_address', 'city',
            'delivery_zone', 'delivery_slot',
            'latitude', 'longitude', 'address_from_map'
        ]

    def __init__(self, *args, **kwargs):
        available_slots = kwargs.pop('available_slots', None)
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': field.label
                })
        if available_slots:
            self.fields['delivery_slot'].choices = [(s, s) for s in available_slots]
    def clean_full_name(self):
        name = self.cleaned_data.get('full_name', '').strip()
        if not re.match(r'^[A-Za-z\s]{3,50}$', name):
            raise forms.ValidationError("Full name should contain only letters and spaces (3–50 characters).")
        return name

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not re.match(r'^[6-9]\d{9}$', phone):
            raise forms.ValidationError("Enter a valid 10-digit phone number starting with 6–9.")
        return phone

    def clean_city(self):
        city = self.cleaned_data.get('city', '').strip()
        if not re.match(r'^[A-Za-z\s]{3,50}$', city):
            raise forms.ValidationError("City name should contain only letters and spaces.")
        return city

    def clean_street_address(self):
        street = self.cleaned_data.get('street_address', '').strip()
        if not re.match(r'^[A-Za-z0-9\s,.-]{3,100}$', street):
            raise forms.ValidationError("Street address can include letters, numbers, commas, periods, hyphens.")
        return street

    def clean(self):
        cleaned_data = super().clean()
        zone = cleaned_data.get('delivery_zone')
        lat = cleaned_data.get('latitude')
        lon = cleaned_data.get('longitude')
        if not zone and (not lat or not lon):
            raise forms.ValidationError("Please select a delivery area/pincode or choose a location on the map.")

        return cleaned_data


class VendorProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'title', 'description', 'base_price', 'weight_options', 'image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control',
                'placeholder': field.label
            })
        self.fields['description'].widget.attrs['rows'] = 3

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message', 'attachment']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your full name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@email.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter 10-digit phone number'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter subject'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Write your message...'}),
            'attachment': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not phone:
            raise forms.ValidationError("Please enter your phone number.")
        phone = phone.strip()
        if not re.match(r'^\d{10}$', phone):
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        return phone

class EditOrderForm(forms.ModelForm):

    delivery_slot = forms.ChoiceField(
        choices=SLOT_CHOICES,
        widget=forms.Select(attrs={
            "class": "form-select"
        })
    )

    class Meta:
        model = Order
        fields = [
            'street_address',
            'city',
            'delivery_zone',
            'delivery_slot',
            'latitude',
            'longitude',
            'address_from_map',
        ]

        widgets = {
            'street_address': forms.TextInput(attrs={"class": "form-control"}),
            'city': forms.TextInput(attrs={"class": "form-control"}),
            'delivery_zone': forms.Select(attrs={"class": "form-select"}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
            'address_from_map': forms.HiddenInput(),
        }

class CancelOrderForm(forms.Form):
    REASON_CHOICES = [
    ("found_cheaper", "Found a cheaper price somewhere else"),
    ("ordered_by_mistake", "Placed the order by mistake"),
    ("payment_issue", "Payment or checkout issues"),
    ("item_not_needed", "No longer need the item"),
    ("duplicate_order", "Accidentally placed a duplicate order"),
    ("wrong_product", "Selected the wrong product"),
    ("delivery_date_unsuitable", "Delivery date is too late"),
    ("size_color_change", "I want to change size or color"),
    ("quantity_issue", "I want to change the quantity"),
    ("not_trusted", "Not comfortable proceeding with this purchase"),

    ("edit_details", "I want to edit delivery details"),
    ("other", "Other reason"),
    ]

    reason = forms.ChoiceField(choices=REASON_CHOICES, widget=forms.Select(attrs={
        "class": "form-select"
    }))

    other_reason = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Write reason here"})
    )

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        "class": "form-control",
        "placeholder": "Enter registered email"
    }))


class OTPVerifyForm(forms.Form):
    otp = forms.CharField(max_length=6, widget=forms.TextInput(attrs={
        "class": "form-control",
        "placeholder": "Enter OTP"
    }))


class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "New Password"
        })
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Confirm Password"
        })
    )
    
    def clean_new_password(self):
        password = self.cleaned_data.get("new_password")

        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")

        if not re.search(r"[A-Z]", password):
            raise ValidationError("Password must contain at least one uppercase letter.")

        if not re.search(r"[a-z]", password):
            raise ValidationError("Password must contain at least one lowercase letter.")

        if not re.search(r"[0-9]", password):
            raise ValidationError("Password must contain at least one number.")

        if re.search(r"\s", password):
            raise ValidationError("Password cannot contain spaces.")

        return password

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("new_password")
        p2 = cleaned.get("confirm_password")

        if p1 and p2 and p1 != p2:
            raise ValidationError("Passwords do not match.")

        return cleaned
