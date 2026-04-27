# """
# Authentication Serializers for Fleet Manager API
# """
#
# from rest_framework import serializers
# from django.contrib.auth import authenticate
# from django.contrib.auth.password_validation import validate_password
# from security.models import CustomUser
# from entity.models import Organization
#
#
# class UserRegistrationSerializer(serializers.ModelSerializer):
#     """
#     Serializer for user registration
#     """
#     password = serializers.CharField(write_only=True, validators=[validate_password])
#     password_confirm = serializers.CharField(write_only=True)
#     organization = serializers.PrimaryKeyRelatedField(
#         queryset=Organization.objects.all(),
#         required=False,
#         allow_null=True
#     )
#
#     class Meta:
#         model = CustomUser
#         fields = [
#             'username', 'email', 'first_name', 'last_name',
#             'phone_number', 'password', 'password_confirm',
#             'organization', 'role'
#         ]
#         extra_kwargs = {
#             'role': {'required': False}
#         }
#
#     def validate(self, attrs):
#         if attrs['password'] != attrs['password_confirm']:
#             raise serializers.ValidationError("Passwords don't match")
#         return attrs
#
#     def create(self, validated_data):
#         validated_data.pop('password_confirm')
#         password = validated_data.pop('password')
#         user = CustomUser.objects.create_user(password=password, **validated_data)
#         return user
#
#
# class UserLoginSerializer(serializers.Serializer):
#     """
#     Serializer for user login
#     """
#     username = serializers.CharField()
#     password = serializers.CharField(write_only=True)
#
#     def validate(self, attrs):
#         username = attrs.get('username')
#         password = attrs.get('password')
#
#         if username and password:
#             user = authenticate(username=username, password=password)
#             if not user:
#                 raise serializers.ValidationError('Invalid credentials')
#             if not user.is_active:
#                 raise serializers.ValidationError('User account is disabled')
#             attrs['user'] = user
#             return attrs
#         else:
#             raise serializers.ValidationError('Must include username and password')
#
#
# class UserProfileSerializer(serializers.ModelSerializer):
#     """
#     Serializer for user profile information
#     """
#     organization_name = serializers.CharField(source='organization.name', read_only=True)
#     role_display = serializers.CharField(source='get_role_display', read_only=True)
#
#     class Meta:
#         model = CustomUser
#         fields = [
#             'id', 'username', 'email', 'first_name', 'last_name',
#             'phone_number', 'organization', 'organization_name',
#             'role', 'role_display', 'is_active', 'date_joined',
#             'last_login'
#         ]
#         read_only_fields = ['id', 'username', 'date_joined', 'last_login']
#
#
# class ChangePasswordSerializer(serializers.Serializer):
#     """
#     Serializer for changing password
#     """
#     old_password = serializers.CharField(write_only=True)
#     new_password = serializers.CharField(write_only=True, validators=[validate_password])
#     new_password_confirm = serializers.CharField(write_only=True)
#
#     def validate(self, attrs):
#         if attrs['new_password'] != attrs['new_password_confirm']:
#             raise serializers.ValidationError("New passwords don't match")
#         return attrs
#
#     def validate_old_password(self, value):
#         user = self.context['request'].user
#         if not user.check_password(value):
#             raise serializers.ValidationError("Old password is incorrect")
#         return value
#
#
# class PasswordResetSerializer(serializers.Serializer):
#     """
#     Serializer for password reset request
#     """
#     email = serializers.EmailField()
#
#     def validate_email(self, value):
#         try:
#             user = CustomUser.objects.get(email=value, is_active=True)
#         except CustomUser.DoesNotExist:
#             raise serializers.ValidationError("No active user found with this email")
#         return value
#
#
# class PasswordResetConfirmSerializer(serializers.Serializer):
#     """
#     Serializer for password reset confirmation
#     """
#     token = serializers.CharField()
#     new_password = serializers.CharField(write_only=True, validators=[validate_password])
#     new_password_confirm = serializers.CharField(write_only=True)
#
#     def validate(self, attrs):
#         if attrs['new_password'] != attrs['new_password_confirm']:
#             raise serializers.ValidationError("Passwords don't match")
#         return attrs
#
#
# class UserListSerializer(serializers.ModelSerializer):
#     """
#     Serializer for listing users (admin only)
#     """
#     organization_name = serializers.CharField(source='organization.name', read_only=True)
#     role_display = serializers.CharField(source='get_role_display', read_only=True)
#     full_name = serializers.SerializerMethodField()
#
#     class Meta:
#         model = CustomUser
#         fields = [
#             'id', 'username', 'email', 'full_name', 'first_name', 'last_name',
#             'phone_number', 'organization', 'organization_name',
#             'role', 'role_display', 'is_active', 'is_staff',
#             'date_joined', 'last_login'
#         ]
#
#     def get_full_name(self, obj):
#         return f"{obj.first_name} {obj.last_name}".strip() or obj.username