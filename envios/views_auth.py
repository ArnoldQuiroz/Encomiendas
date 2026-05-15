# envios/views_auth.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Bienvenido, {user.username}!')
            next_page = request.GET.get('next', 'dashboard')
            return redirect(next_page)
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente.')
    return redirect('login')


@login_required
def perfil_view(request):
    return render(request, 'accounts/perfil.html', {'user': request.user})


@login_required
def configuracion_view(request):
    """⚙️ Página de configuración del usuario."""
    from django.contrib.auth.forms import PasswordChangeForm
    from django.contrib.auth import update_session_auth_hash

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'datos':
            request.user.first_name = request.POST.get('first_name', '').strip()
            request.user.last_name  = request.POST.get('last_name',  '').strip()
            request.user.email      = request.POST.get('email',      '').strip()
            request.user.save()
            messages.success(request, '✓ Datos actualizados correctamente.')
            return redirect('configuracion')

        elif action == 'password':
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, '✓ Contraseña actualizada correctamente.')
                return redirect('configuracion')
            else:
                for field, errs in form.errors.items():
                    for e in errs:
                        messages.error(request, e)

    return render(request, 'accounts/configuracion.html')