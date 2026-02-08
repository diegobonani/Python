from django.contrib import admin
from .models import Perfil, HistoricoResetPontos, UsuarioLegado

@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    
    # --- 1. CONFIGURAÇÃO DA LISTA ---
    # Adicionado 'get_ra' para visualizar o RA diretamente na tabela
    list_display = ('nome_completo', 'tipo', 'responsavel', 'get_ra', 'esta_estudando')
    list_filter = ('tipo', 'esta_estudando', 'ra_uf')
    search_fields = ('nome_completo', 'usuario__username', 'ra_numero')

    # --- 2. ORGANIZAÇÃO DOS CAMPOS (Fieldsets) ---
    fieldsets = (
        ('Informações Principais', {
            'fields': ('usuario', 'tipo', 'nome_completo', 'responsavel')
        }),
        ('Status Atual (Jornada)', {
            'fields': ('esta_trabalhando', 'esta_estudando')
        }),
        # NOVA SEÇÃO: Integração SED (RA e Senha)
        ('Integração Escolar (SED / Robô)', {
            'classes': ('collapse',), 
            'fields': ('ra_numero', 'ra_digito', 'ra_uf', 'senha_sed'),
            'description': 'Dados necessários para o robô buscar o boletim automaticamente.'
        }),
        ('Dados Pessoais (Operacional)', {
            'classes': ('collapse',), 
            'fields': ('sexo', 'data_nascimento', 'altura', 'peso')
        }),
        ('Documentos Sensíveis', {
            'classes': ('collapse',),
            'fields': ('rg', 'cpf', 'cnh')
        }),
        ('Configuração Financeira', {
            'classes': ('collapse',),
            'fields': ('valor_hora', 'percentual_hora_extra')
        }),
    )

    # --- 3. FUNÇÕES AUXILIARES ---
    def get_ra(self, obj):
        if obj.ra_numero:
            return f"{obj.ra_numero}-{obj.ra_digito} {obj.ra_uf}"
        return "-"
    get_ra.short_description = "RA Escolar"

    # --- 4. LÓGICA DE HIERARQUIA ---
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = []

        if obj:
            readonly_fields.append('usuario')

        if not request.user.is_superuser:
            readonly_fields.extend([
                'tipo', 'rg', 'cpf', 'cnh',
                'valor_hora', 'percentual_hora_extra'
            ])
            
        return readonly_fields

    # --- 5. PERMISSÕES ---
    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

# Registrando os outros modelos do app Usuarios para não dar erro
admin.site.register(HistoricoResetPontos)
admin.site.register(UsuarioLegado)