from django.shortcuts import render, redirect

def intro_view(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    return render(request, 'main.html')


def home_view(request):
    if not request.user.is_authenticated:
        return redirect('intro')
        
    return render(request, 'home/home.html')

def game_view(request):
    if not request.user.is_authenticated:
        return redirect('intro')
    return render(request, 'main/game/game.html')