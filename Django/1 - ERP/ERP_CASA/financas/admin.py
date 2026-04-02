# financas/admin.py
from django.contrib import admin
from .models import FormaPagamento, Financa, FinancaComprovante, FinancaCategoria

# -----------------------------------------------------------------
# Modelos Globais (Sem filtro, todos podem ver)
# -----------------------------------------------------------------

# Categoria de Finança (ex: Moradia, Lazer) - Global
class FinancaCategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo_custo')
    search_fields = ('nome',)
admin.site.register(FinancaCategoria, FinancaCategoriaAdmin)

# Forma de Pagamento (ex: Pix, Crédito) - Global
class FormaPagamentoAdmin(admin.ModelAdmin):
    list_display = ('nome',)
admin.site.register(FormaPagamento, FormaPagamentoAdmin)


# -----------------------------------------------------------------
# Modelos Filtrados (Cada usuário só vê o que é seu)
# -----------------------------------------------------------------

@admin.register(Financa)
class FinancaAdmin(admin.ModelAdmin):
    """
    Classe de Admin para o modelo Financa.
    Aplica filtros para que Super Users e Administradores vejam tudo,
    mas Usuários Comuns vejam apenas seus próprios lançamentos.
    """
    list_display = ('nome', 'usuario', 'tipo', 'valor', 'data_registro', 'conta')
    list_filter = ('tipo', 'conta', 'data_registro', 'usuario') # 'usuario' será filtrado automaticamente
    search_fields = ('nome', 'descricao', 'usuario__username')

    def get_queryset(self, request):
        """
        Filtra a lista principal (o queryset)
        """
        # Pega o queryset padrão (todos os objetos)
        qs = super().get_queryset(request)

        # Se for Super User ou do grupo Administradores, pode ver TUDO
        if request.user.is_superuser or request.user.groups.filter(name='Administradores').exists():
            return qs

        # Se for Usuário Comum, filtra para mostrar apenas os seus
        return qs.filter(usuario=request.user)

    def save_model(self, request, obj, form, change):
        """
        Ao salvar um novo objeto (change=False),
        define automaticamente o campo 'usuario' como o usuário logado.
        """
        if not change: # 'change' é False quando está criando um novo
            obj.usuario = request.user
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        """
        Customiza o formulário de adição/edição.
        """
        form = super().get_form(request, obj, **kwargs)
        
        # Se NÃO for Super User ou Administrador...
        if not (request.user.is_superuser or request.user.groups.filter(name='Administradores').exists()):
            # ... e o campo 'usuario' existir no formulário...
            if 'usuario' in form.base_fields:
                # ... desabilita o campo 'usuario'.
                # Isso impede que um Usuário Comum crie um lançamento
                # em nome de OUTRO usuário.
                form.base_fields['usuario'].disabled = True
        return form

    def has_change_permission(self, request, obj=None):
        """
        Segurança extra: Usuário Comum só pode alterar seus próprios objetos.
        """
        if request.user.is_superuser or request.user.groups.filter(name='Administradores').exists():
            return True # Admins/SU podem alterar tudo
            
        if obj is not None and obj.usuario != request.user:
            return False # Nega permissão se o objeto não for do usuário
            
        return True # Permite a ação (ou é 'add' (obj=None) or o obj é dele)

    def has_delete_permission(self, request, obj=None):
        """
        Segurança extra: Usuário Comum só pode deletar seus próprios objetos.
        """
        # Reutiliza a mesma lógica da permissão de alterar
        return self.has_change_permission(request, obj)


@admin.register(FinancaComprovante)
class FinancaComprovanteAdmin(admin.ModelAdmin):
    """
    Classe de Admin para os Comprovantes.
    Aplica a mesma lógica de filtro, baseando-se no 'dono'
    da finança associada.
    """
    list_display = ('financa', 'descricao', 'data_envio')
    search_fields = ('financa__nome', 'descricao')

    def get_queryset(self, request):
        """
        Filtra a lista principal (o queryset)
        """
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.groups.filter(name='Administradores').exists():
            return qs
            
        # Filtra os comprovantes mostrando apenas aqueles
        # cuja 'financa' pertence ao usuário logado.
        return qs.filter(financa__usuario=request.user)

    def get_form(self, request, obj=None, **kwargs):
        """
        Customiza o formulário (principalmente o dropdown 'financa')
        """
        form = super().get_form(request, obj, **kwargs)
        
        # Se NÃO for Super User ou Administrador...
        if not (request.user.is_superuser or request.user.groups.filter(name='Administradores').exists()):
            # ...filtra o campo 'financa' para mostrar
            # apenas as finanças que pertencem ao usuário.
            if 'financa' in form.base_fields:
                form.base_fields['financa'].queryset = Financa.objects.filter(usuario=request.user)
        return form
        
    def has_change_permission(self, request, obj=None):
        """
        Segurança: Usuário Comum só pode alterar seus próprios comprovantes.
        """
        if request.user.is_superuser or request.user.groups.filter(name='Administradores').exists():
            return True
        if obj is not None and obj.financa.usuario != request.user:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        """
        Segurança: Usuário Comum só pode deletar seus próprios comprovantes.
        """
        return self.has_change_permission(request, obj)

# NOTA: Os modelos Financa e FinancaComprovante são registrados usando
# o @admin.register(Modelo) acima.