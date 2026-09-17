from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import RegistroForm


def hola(request):
    return redirect('producto' if request.user.is_authenticated else 'login')


def registro(request):
    if request.user.is_authenticated:
        return redirect('producto')
    form = RegistroForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('producto')
    return render(request, 'registration/registro.html', {'form': form})
