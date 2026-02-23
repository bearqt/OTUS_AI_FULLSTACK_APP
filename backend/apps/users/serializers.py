from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
  display_name = serializers.SerializerMethodField()

  class Meta:
    model = User
    fields = ("id", "username", "email", "full_name", "display_name")

  def get_display_name(self, obj):
    return obj.full_name or obj.username


class RegisterSerializer(serializers.ModelSerializer):
  password = serializers.CharField(write_only=True, min_length=8)
  password_confirm = serializers.CharField(write_only=True, min_length=8)

  class Meta:
    model = User
    fields = ("username", "email", "full_name", "password", "password_confirm")

  def validate_email(self, value):
    email = value.strip().lower()
    if User.objects.filter(email__iexact=email).exists():
      raise serializers.ValidationError("User with this email already exists.")
    return email

  def validate_username(self, value):
    username = value.strip()
    if not username:
      raise serializers.ValidationError("Username is required.")
    if User.objects.filter(username__iexact=username).exists():
      raise serializers.ValidationError("User with this username already exists.")
    return username

  def validate(self, attrs):
    if attrs["password"] != attrs["password_confirm"]:
      raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
    validate_password(attrs["password"])
    return attrs

  @transaction.atomic
  def create(self, validated_data):
    validated_data.pop("password_confirm", None)
    password = validated_data.pop("password")
    user = User(**validated_data)
    user.email = user.email.lower()
    user.set_password(password)
    user.save()
    return user


class MiniTrelloTokenObtainPairSerializer(TokenObtainPairSerializer):
  @classmethod
  def get_token(cls, user):
    token = super().get_token(user)
    token["username"] = user.username
    token["email"] = user.email
    return token

  def validate(self, attrs):
    data = super().validate(attrs)
    data["user"] = UserSerializer(self.user).data
    return data
