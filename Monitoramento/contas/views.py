from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout


@login_required(login_url='/admin/login/') 
def dashboard(request):
    # Mudamos aqui para renderizar a página específica
    return render(request, 'contas/dashboard.html')

def sair(request):
    logout(request)
    return redirect('/admin/login')