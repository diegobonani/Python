from django.contrib import admin
from .models import Perfil

# Adiciona filtros e campos de busca para facilitar a administração
@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    
    # --- 1. CONFIGURAÇÃO DA LISTA ---
    # Adicionamos os novos campos booleanos à lista principal
    list_display = ('usuario', 'nome_completo', 'tipo', 'esta_trabalhando', 'esta_estudando')
    list_filter = ('tipo', 'esta_trabalhando', 'esta_estudando')
    search_fields = ('nome_completo', 'usuario__username')

    # --- 2. ORGANIZAÇÃO DOS CAMPOS (Fieldsets) ---
    # Organizamos todos os campos do seu 'models.py' em seções
    fieldsets = (
        # Seção 1: Informações Principais
        ('Informações Principais', {
            'fields': ('usuario', 'tipo', 'nome_completo')
        }),
        # Seção 2: Status Atual (Gestor pode editar)
        ('Status Atual (Jornada)', {
            'fields': ('esta_trabalhando', 'esta_estudando')
        }),
        # Seção 3: Dados Pessoais (Gestor pode editar)
        ('Dados Pessoais (Operacional)', {
            'classes': ('collapse',), # Começa fechado para limpar a tela
            'fields': ('sexo', 'data_nascimento', 'altura', 'peso')
        }),
        # Seção 4: Dados Sensíveis (SÓ O CEO PODE EDITAR)
        ('Documentos Sensíveis (Somente Super-usuário pode editar)', {
            'classes': ('collapse',),
            'fields': ('rg', 'cpf', 'cnh')
        }),
        # Seção 5: Financeiro (SÓ O CEO PODE EDITAR)
        ('Configuração Financeira (Somente Super-usuário pode editar)', {
            'classes': ('collapse',),
            'fields': ('valor_hora', 'percentual_hora_extra')
        }),
    )

    # --- 3. LÓGICA DE HIERARQUIA (A "MÁGICA") ---
    
    def get_readonly_fields(self, request, obj=None):
        """
        Esta função define quais campos serão "somente leitura"
        baseado no usuário logado (request.user).
        """
        # Primeiro, define um conjunto base de campos bloqueados
        readonly_fields = []

        # Se o objeto já existe (edição), bloqueia o campo 'usuario' para todos.
        # Isso impede que alguém troque o Perfil de um usuário para outro.
        if obj:
            readonly_fields.append('usuario')

        # Agora, a regra de hierarquia:
        # Se o usuário NÃO for um Super User (ou seja, ele é um "Gestor" como o diegobonani)...
        if not request.user.is_superuser:
            # ...adiciona todos os campos sensíveis e financeiros à lista de bloqueados.
            readonly_fields.extend([
                'tipo', # Gestor não pode promover ou rebaixar outros
                'rg',
                'cpf',
                'cnh',
                'valor_hora',
                'percentual_hora_extra'
            ])
            
        # Retorna a lista de campos que devem ser bloqueados
        return readonly_fields

    # --- 4. PERMISSÕES ADICIONAIS ---
    
    def has_change_permission(self, request, obj=None):
        # Permite que o "Gestor" acesse a página de edição 
        # (os campos sensíveis estarão bloqueados pela função acima)
        return True

    def has_delete_permission(self, request, obj=None):
        # Regra de segurança: Apenas o "CEO" (Super User) pode deletar um Perfil.
        return request.user.is_superuser