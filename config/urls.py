"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name="index.html"), name="home" ),
    path('login/', TemplateView.as_view(template_name="login.html"), name="login" ),
    path('signup/', TemplateView.as_view(template_name="register.html"), name="register" ),
    path('profile/', TemplateView.as_view(template_name="user_page.html"), name="profile" ),
    path('search/', TemplateView.as_view(template_name="search.html"), name="search" ),
    path('trendingvideo/', TemplateView.as_view(template_name="trendingvideo.html"), name="trendingvideo" ),
    path('category/', TemplateView.as_view(template_name="category.html"), name="category" ),
    path('reelsseasonal/', TemplateView.as_view(template_name="reelsseasonal.html"), name="reelsseasonal" ),
    path('contact/', TemplateView.as_view(template_name="contact.html"), name="contact" ),
    # Include fashion app URLs for Instagram reels search functionality
    path('fashion/', include('fashion.urls')),
    # path('mens/', TemplateView.as_view(template_name="mens.html"), name="mens" ),
    # path('womens/', TemplateView.as_view(template_name="womens.html"), name="womens" ),
    path('fashion/', include("fashion.urls"), name="fashion" ),#import all files which is create in App
]