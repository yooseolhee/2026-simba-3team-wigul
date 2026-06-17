from django.shortcuts import render

# Create your views here.
def home_view(request):
    return render(request, 'main.html')

def signup_view(request):
    return render(request, 'main/signup.html')

def login_view(request):
    return render(request, 'main/login.html')