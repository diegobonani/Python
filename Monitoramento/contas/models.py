import re, random, string
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

OPCOES_TIPO_ACESSO = (
    ('CEO', 'Administrador / Dono'),
    ('GERENTE', 'Gerente de Loja'),
    ('OPERACIONAL', 'Operador de Caixa / Balcão'),
)

class GerenciadorUsuario(BaseUserManager):
    
    def create_user(self, ru, email, cnpj, password=None, **campos_extras):
        if not email:
            raise ValueError('O endereço de e-mail é obrigatório.')
        if not cnpj:
            raise ValueError('O CNPJ é obrigatório.')
        
        email = self.normalize_email(email)
        cnpj_limpo = re.sub(r'[^0-9]', '', cnpj) # Remove pontos e traços
        
        usuario = self.model(ru=ru, email=email, cnpj=cnpj_limpo, **campos_extras)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, ru, email, cnpj, password=None, **campos_extras):
        campos_extras.setdefault('is_staff', True)
        campos_extras.setdefault('is_superuser', True)
        
       
        if not ru:
            ru = ""
            
        return self.create_user(ru, email, cnpj, password, **campos_extras)

class UsuarioUnidade(AbstractBaseUser, PermissionsMixin):
    
    ru = models.CharField(max_length=50, unique=True, blank=True, verbose_name='Registro de Unidade (RU)')
    cnpj = models.CharField(max_length=18, unique=True, verbose_name='CNPJ da Unidade')
    email = models.EmailField(unique=True, verbose_name='E-mail do Cliente')
    
    perfil = models.CharField(
        max_length=20, 
        choices=OPCOES_TIPO_ACESSO, 
        default='OPERACIONAL', 
        verbose_name='Nível de Acesso'
    )
    
    primeiro_acesso = models.BooleanField(default=True, verbose_name='Deve trocar a senha?')
    is_active = models.BooleanField(default=True, verbose_name='Usuário Ativo')
    is_staff = models.BooleanField(default=False, verbose_name='Tem Acesso ao Painel Admin')
    
    objects = GerenciadorUsuario()

    USERNAME_FIELD = 'ru'
    REQUIRED_FIELDS = ['email', 'cnpj', 'perfil']

    def save(self, *args, **kwargs):
        
        if not self.ru:
            cnpj_numeros = re.sub(r'[^0-9]', '', self.cnpj)
        
            final_cnpj = cnpj_numeros[-4:] if len(cnpj_numeros) >= 4 else "0000"
            
            hash_aleatorio = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            
            self.ru = f"{final_cnpj}-{hash_aleatorio}"
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ru} - {self.get_perfil_display()}"