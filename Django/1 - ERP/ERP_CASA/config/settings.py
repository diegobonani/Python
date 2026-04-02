import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-9xx4k&cn^k-wdwg+_5b-^-d(-djwav616!uvfbh(h%!!7$#@v5'

# SECURITY WARNING: don't run with debug turned on in production!
# CORREÇÃO: Deve ser 'True' durante o desenvolvimento
DEBUG = True

# Adiciona os hosts de desenvolvimento permitidos
ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    # Django Apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-Party Apps (deixamos o espaço para o futuro)

    # Local Apps (NOSSOS APPS)
    'alimentacao.apps.AlimentacaoConfig',
    'carro.apps.CarroConfig',
    'core.apps.CoreConfig',  
    'deslocamento.apps.DeslocamentoConfig',  
    'estoque.apps.EstoqueConfig',
    'financas.apps.FinancasConfig',
    'jornada.apps.JornadaConfig',
    'lavanderia.apps.LavanderiaConfig',
    'rede.apps.RedeConfig',
    'rotinas.apps.RotinasConfig',
    'usuarios.apps.UsuariosConfig',
    
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'casa',            # O nome do seu banco de dados
        'USER': 'root',         # Seu usuário do MySQL (geralmente 'root' em ambiente local)
        'PASSWORD': '2725105Dba',    # A senha do seu usuário do MySQL
        'HOST': 'localhost',        # Ou 127.0.0.1
        'PORT': '3306',             # A porta padrão do MySQL
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'pt-BR'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# Informa ao Django onde encontrar a pasta 'static' principal do seu projeto.
# CORREÇÃO: Removida a definição duplicada do 'BASE_DIR' daqui
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'redirect' # Redireciona para nossa view que decide o dashboard
LOGOUT_REDIRECT_URL = 'login'

AUTHENTICATION_BACKENDS = [
    'usuarios.backends.LegacyUserBackend',      # Nosso backend customizado primeiro
    'django.contrib.auth.backends.ModelBackend', # O backend padrão do Django como fallback
]

TOM_TOM_API_KEY = '0vtXJq3LIbbSBykOu8sDMtgRnoueb6QI'