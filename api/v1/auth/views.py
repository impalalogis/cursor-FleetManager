# """
# Authentication Views for Fleet Manager API
# """
#
# from rest_framework import status, permissions
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.response import Response
# from rest_framework.views import APIView
# from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
# from rest_framework_simplejwt.tokens import RefreshToken
# from rest_framework_simplejwt.views import TokenObtainPairView
# from django.contrib.auth import login, logout
# from django.contrib.auth.tokens import default_token_generator
# from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
# from django.utils.encoding import force_bytes, force_str
# from django.core.mail import send_mail
# from django.conf import settings
# from drf_spectacular.utils import extend_schema, OpenApiParameter
#
# from security.models import CustomUser
# from api.utils import success_response, error_response
# from .serializers import (
#     UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
#     ChangePasswordSerializer, PasswordResetSerializer, PasswordResetConfirmSerializer,
#     UserListSerializer
# )
#
#
# class CustomTokenObtainPairView(TokenObtainPairView):
#     """
#     Custom JWT token obtain view with additional user information
#     """
#     @extend_schema(
#         summary="Obtain JWT token pair",
#         description="Login with username/password to get access and refresh tokens"
#     )
#     def post(self, request, *args, **kwargs):
#         response = super().post(request, *args, **kwargs)
#         if response.status_code == 200:
#             # Add user information to response
#             serializer = UserLoginSerializer(data=request.data)
#             if serializer.is_valid():
#                 user = serializer.validated_data['user']
#                 user_data = UserProfileSerializer(user).data
#                 response.data['user'] = user_data
#         return response
#
#
# class UserRegistrationView(APIView):
#     """
#     User registration endpoint
#     """
#     permission_classes = [permissions.AllowAny]
#
#     @extend_schema(
#         summary="Register new user",
#         description="Create a new user account",
#         request=UserRegistrationSerializer,
#         responses={201: UserProfileSerializer}
#     )
#     def post(self, request):
#         serializer = UserRegistrationSerializer(data=request.data)
#         if serializer.is_valid():
#             user = serializer.save()
#
#             # Generate tokens
#             refresh = RefreshToken.for_user(user)
#
#             # Prepare response data
#             user_data = UserProfileSerializer(user).data
#
#             return success_response(
#                 data={
#                     'user': user_data,
#                     'tokens': {
#                         'access': str(refresh.access_token),
#                         'refresh': str(refresh)
#                     }
#                 },
#                 message="User registered successfully",
#                 status_code=201
#             )
#
#         return error_response(
#             message="Registration failed",
#             details=serializer.errors,
#             status_code=400
#         )
#
#
# class UserProfileView(RetrieveUpdateAPIView):
#     """
#     User profile view for authenticated users
#     """
#     serializer_class = UserProfileSerializer
#     permission_classes = [permissions.IsAuthenticated]
#
#     def get_object(self):
#         return self.request.user
#
#     @extend_schema(
#         summary="Get user profile",
#         description="Retrieve current user's profile information"
#     )
#     def get(self, request, *args, **kwargs):
#         return super().get(request, *args, **kwargs)
#
#     @extend_schema(
#         summary="Update user profile",
#         description="Update current user's profile information"
#     )
#     def put(self, request, *args, **kwargs):
#         return super().put(request, *args, **kwargs)
#
#     @extend_schema(
#         summary="Partially update user profile",
#         description="Partially update current user's profile information"
#     )
#     def patch(self, request, *args, **kwargs):
#         return super().patch(request, *args, **kwargs)
#
#
# class ChangePasswordView(APIView):
#     """
#     Change password endpoint
#     """
#     permission_classes = [permissions.IsAuthenticated]
#
#     @extend_schema(
#         summary="Change password",
#         description="Change current user's password",
#         request=ChangePasswordSerializer
#     )
#     def post(self, request):
#         serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
#         if serializer.is_valid():
#             user = request.user
#             user.set_password(serializer.validated_data['new_password'])
#             user.save()
#
#             return success_response(
#                 message="Password changed successfully"
#             )
#
#         return error_response(
#             message="Password change failed",
#             details=serializer.errors,
#             status_code=400
#         )
#
#
# class PasswordResetView(APIView):
#     """
#     Password reset request endpoint
#     """
#     permission_classes = [permissions.AllowAny]
#
#     @extend_schema(
#         summary="Request password reset",
#         description="Send password reset email to user",
#         request=PasswordResetSerializer
#     )
#     def post(self, request):
#         serializer = PasswordResetSerializer(data=request.data)
#         if serializer.is_valid():
#             email = serializer.validated_data['email']
#             try:
#                 user = CustomUser.objects.get(email=email, is_active=True)
#
#                 # Generate reset token
#                 token = default_token_generator.make_token(user)
#                 uid = urlsafe_base64_encode(force_bytes(user.pk))
#
#                 # Send email (implement based on your email backend)
#                 reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"
#
#                 send_mail(
#                     subject="Password Reset - Fleet Manager",
#                     message=f"Click the link to reset your password: {reset_url}",
#                     from_email=settings.DEFAULT_FROM_EMAIL,
#                     recipient_list=[email],
#                     fail_silently=False,
#                 )
#
#                 return success_response(
#                     message="Password reset email sent"
#                 )
#             except Exception as e:
#                 return error_response(
#                     message="Failed to send password reset email",
#                     details=str(e)
#                 )
#
#         return error_response(
#             message="Invalid email",
#             details=serializer.errors,
#             status_code=400
#         )
#
#
# class PasswordResetConfirmView(APIView):
#     """
#     Password reset confirmation endpoint
#     """
#     permission_classes = [permissions.AllowAny]
#
#     @extend_schema(
#         summary="Confirm password reset",
#         description="Reset password using token from email",
#         request=PasswordResetConfirmSerializer
#     )
#     def post(self, request, uid, token):
#         serializer = PasswordResetConfirmSerializer(data=request.data)
#         if serializer.is_valid():
#             try:
#                 user_id = force_str(urlsafe_base64_decode(uid))
#                 user = CustomUser.objects.get(pk=user_id)
#
#                 if default_token_generator.check_token(user, token):
#                     user.set_password(serializer.validated_data['new_password'])
#                     user.save()
#
#                     return success_response(
#                         message="Password reset successfully"
#                     )
#                 else:
#                     return error_response(
#                         message="Invalid or expired token",
#                         status_code=400
#                     )
#             except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
#                 return error_response(
#                     message="Invalid reset link",
#                     status_code=400
#                 )
#
#         return error_response(
#             message="Invalid data",
#             details=serializer.errors,
#             status_code=400
#         )
#
#
# class UserListView(ListAPIView):
#     """
#     List all users (admin only)
#     """
#     queryset = CustomUser.objects.all()
#     serializer_class = UserListSerializer
#     permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
#     filterset_fields = ['is_active', 'role', 'organization']
#     search_fields = ['username', 'email', 'first_name', 'last_name']
#     ordering_fields = ['username', 'email', 'date_joined']
#     ordering = ['-date_joined']
#
#     @extend_schema(
#         summary="List users",
#         description="Get list of all users (admin only)",
#         parameters=[
#             OpenApiParameter('is_active', bool, description='Filter by active status'),
#             OpenApiParameter('role', str, description='Filter by user role'),
#             OpenApiParameter('organization', int, description='Filter by organization ID'),
#             OpenApiParameter('search', str, description='Search in username, email, name'),
#         ]
#     )
#     def get(self, request, *args, **kwargs):
#         return super().get(request, *args, **kwargs)
#
#
# @extend_schema(
#     summary="Logout user",
#     description="Logout current user and blacklist refresh token"
# )
# @api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated])
# def logout_view(request):
#     """
#     Logout endpoint
#     """
#     try:
#         refresh_token = request.data.get('refresh_token')
#         if refresh_token:
#             token = RefreshToken(refresh_token)
#             token.blacklist()
#
#         logout(request)
#         return success_response(message="Logged out successfully")
#     except Exception as e:
#         return error_response(
#             message="Logout failed",
#             details=str(e)
#         )
#
#
# @extend_schema(
#     summary="Get current user info",
#     description="Get current authenticated user information"
# )
# @api_view(['GET'])
# @permission_classes([permissions.IsAuthenticated])
# def current_user_view(request):
#     """
#     Get current user information
#     """
#     serializer = UserProfileSerializer(request.user)
#     return success_response(data=serializer.data)