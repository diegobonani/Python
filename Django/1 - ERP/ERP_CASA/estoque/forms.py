from django import forms
from django.contrib.auth.models import User
from django.db.models import Q
from django.apps import apps # Usaremos apps.get_model para evitar erros de importação

from core.models import EstoqueCategoria, Unidade, Setor, Pet
from .models import (
    Comodo, Localizacao, 
    ListaCompra, ListaCompraProduto, 
    SimulacaoCenario, SimulacaoItem,
    CatalogoPessoal, ItemFaltante
)

# ==============================================================================
# HELPER: FUNÇÃO AUXILIAR PARA EVITAR ERROS DE CONVERSÃO
# ==============================================================================
def converter_para_float(valor):
    if valor is None or valor == "": return 0.0
    if isinstance(valor, (float, int, complex)): return float(valor)
    
    str_val = str(valor).strip().replace('R$', '').strip()
    
    try:
        if ',' in str_val and '.' in str_val:
             return float(str_val.replace('.', '').replace(',', '.'))
        elif ',' in str_val:
            return float(str_val.replace(',', '.'))
        else:
            return float(str_val)
    except ValueError: 
        return 0.0

# ==============================================================================
# 1. FORMULÁRIO GENÉRICO DE ESTOQUE
# ==============================================================================
class EstoqueForm(forms.Form):
    form_type = forms.CharField(required=False, widget=forms.HiddenInput())
    nome_item = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do Item'}))
    setor = forms.ModelChoiceField(queryset=Setor.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select'}), empty_label="Selecione")
    categoria = forms.ModelChoiceField(queryset=EstoqueCategoria.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    unidade = forms.ModelChoiceField(queryset=Unidade.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    quantidade = forms.CharField(required=False, initial="1", widget=forms.TextInput(attrs={'class': 'form-control'}))
    estoque_minimo = forms.CharField(required=False, initial="1", widget=forms.TextInput(attrs={'class': 'form-control'}))
    estoque_ideal = forms.CharField(required=False, initial="2", widget=forms.TextInput(attrs={'class': 'form-control'}))
    preco_unitario = forms.CharField(required=False, initial="0,00", widget=forms.TextInput(attrs={'class': 'form-control'}))
    valor_total_estoque = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    data_validade = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    comodo = forms.ModelChoiceField(queryset=Comodo.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    localizacao = forms.ModelChoiceField(queryset=Localizacao.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select'}))

    def clean(self):
        cleaned_data = super().clean()
        unidade_obj = cleaned_data.get('unidade') 
        setor_obj = cleaned_data.get('setor')      
        nome_unidade = str(unidade_obj).upper() if unidade_obj else ""
        nome_setor = str(setor_obj).upper() if setor_obj else ""
        form_type = cleaned_data.get('form_type')

        if not setor_obj and form_type:
            termo_busca = ""
            if form_type == 'casa': termo_busca = 'Casa'
            elif form_type == 'pet': termo_busca = 'Pet'
            elif form_type == 'usuario': termo_busca = 'Usuário'
            if termo_busca:
                setor_encontrado = Setor.objects.filter(Q(nome__icontains=termo_busca) | Q(nome__icontains=termo_busca.replace('á', 'a'))).first()
                if setor_encontrado:
                    cleaned_data['setor'] = setor_encontrado
                    setor_obj = setor_encontrado

        if not setor_obj:
            self.add_error('setor', "O setor é obrigatório.")

        campos_validar = ['quantidade', 'estoque_minimo', 'estoque_ideal']
        for campo in campos_validar:
            val_raw = cleaned_data.get(campo)
            val_float = converter_para_float(val_raw)
            if val_float is None and val_raw: self.add_error(campo, "Número inválido."); continue
            if val_float is None: continue
            if val_float < 0: self.add_error(campo, "Não pode ser negativo."); continue
            
            tem_decimal = (val_float % 1) != 0
            if "USUARIO" in nome_setor or "USUÁRIO" in nome_setor:
                if tem_decimal: self.add_error(campo, "Setor Usuário aceita apenas inteiros.")
            else:
                unidades_fracionadas = ['KILO', 'KG', 'LITRO', 'L', 'LT', 'METRO', 'M', 'ML', 'GR', 'GRAMA']
                eh_fracionado = any(u in nome_unidade for u in unidades_fracionadas)
                if not eh_fracionado and tem_decimal: self.add_error(campo, f"A unidade selecionada exige número inteiro.")
        return cleaned_data

# ==============================================================================
# 2. FORMULÁRIOS DO ASSISTENTE DE REPOSIÇÃO
# ==============================================================================
class CatalogoPessoalForm(forms.ModelForm):
    class Meta:
        model = CatalogoPessoal
        fields = ['setor', 'nome', 'categoria']
        widgets = {
            'setor': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'nome': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'categoria': forms.Select(attrs={'class': 'form-select form-select-sm'}), 
        }

class ItemFaltanteForm(forms.ModelForm):
    setor_destino = forms.ChoiceField(choices=CatalogoPessoal.SETOR_CHOICES, initial='USUARIO', widget=forms.Select(attrs={'class': 'form-select form-select-sm', 'id': 'id_setor_destino'}))
    item_catalogo = forms.ModelChoiceField(queryset=CatalogoPessoal.objects.all().order_by('nome'), widget=forms.Select(attrs={'class': 'form-select form-select-sm', 'id': 'id_item_catalogo'}))
    quantidade = forms.CharField(initial="1", widget=forms.TextInput(attrs={'class': 'form-control form-select-sm', 'id': 'id_quantidade'}))
    unidade = forms.ModelChoiceField(queryset=Unidade.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select form-select-sm', 'id': 'id_unidade'}))
    destinatarios = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}), required=True)

    class Meta:
        model = ItemFaltante
        fields = ['prioridade', 'observacao']
        widgets = {
            'prioridade': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'observacao': forms.TextInput(attrs={'class': 'form-control form-select-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        un_padrao = Unidade.objects.filter(sigla='UN').first()
        if un_padrao: self.fields['unidade'].initial = un_padrao
        
        choices = []
        qs_users = User.objects.all().order_by('username')
        choices_users = [('TODOS', 'Todos')] + [(str(u.id), u.username) for u in qs_users]
        
        if self.data and self.data.get('setor_destino'):
            setor = self.data.get('setor_destino')
            if setor == 'PET':
                qs_pets = Pet.objects.all().order_by('nome_pet')
                choices = [('TODOS', 'Todos')] + [(str(p.id), p.nome_pet) for p in qs_pets]
            elif setor == 'CASA':
                qs_locais = Localizacao.objects.select_related('comodo').all().order_by('comodo__nome', 'nome')
                choices = [('TODOS', 'Todos')] + [(str(l.id), f"{l.comodo.nome} > {l.nome}") for l in qs_locais]
            else: choices = choices_users
        else: choices = choices_users
        self.fields['destinatarios'].choices = choices

# ==============================================================================
# 3. OUTROS FORMULÁRIOS
# ==============================================================================
class ListaCompraForm(forms.ModelForm):
    class Meta:
        model = ListaCompra
        fields = ['supermercado', 'cidade', 'data_compra', 'valor_total']
        widgets = {
            'data_compra': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'supermercado': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'valor_total': forms.TextInput(attrs={'class': 'form-control currency-input'}),
        }

class ListaCompraProdutoForm(forms.ModelForm):
    adicionar_ao_estoque = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    comodo_destino = forms.ModelChoiceField(queryset=Comodo.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    class Meta:
        model = ListaCompraProduto
        fields = ['nome', 'marca', 'quantidade', 'unidade', 'valor_unit']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'quantidade': forms.TextInput(attrs={'class': 'form-control'}),
            'unidade': forms.Select(attrs={'class': 'form-select'}),
            'valor_unit': forms.TextInput(attrs={'class': 'form-control currency-input'}),
        }

class SimulacaoCenarioForm(forms.ModelForm):
    class Meta: model = SimulacaoCenario; fields = ['nome']; widgets = {'nome': forms.TextInput(attrs={'class': 'form-control'})}

class SimulacaoItemForm(forms.ModelForm):
    class Meta:
        model = SimulacaoItem
        fields = ['nome_item', 'preco_estimado', 'quantidade', 'observacoes']
        widgets = {
            'nome_item': forms.TextInput(attrs={'class': 'form-control'}),
            'preco_estimado': forms.TextInput(attrs={'class': 'form-control currency-input'}),
            'quantidade': forms.TextInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

# ==============================================================================
# 4. FORMULÁRIO DE LANÇAMENTO FINANCEIRO (CORRIGIDO)
# ==============================================================================
class LancarDespesaCompraForm(forms.Form):
    """
    Formulário de Lançamento Financeiro com Filtro Dinâmico.
    """
    # 1. Campo para Filtrar (Não salva nada, só ajuda a escolher)
    filtro_usuario = forms.ChoiceField(
        label="Filtrar por Usuário",
        required=False,
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_filtro_usuario_despesa'})
    )

    # 2. Campo Real (Conta que sofrerá o débito)
    conta = forms.ModelChoiceField(
        queryset=None, 
        required=True, 
        label="Conta de Pagamento",
        empty_label="Selecione o usuário primeiro...",
        widget=forms.Select(attrs={'class': 'form-select fw-bold', 'id': 'id_conta_despesa'})
    )

    def __init__(self, *args, **kwargs):
        usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        
        # Busca o model de Conta de forma segura
        try:
            ContaModel = apps.get_model('financas', 'Conta')
        except LookupError:
            try:
                ContaModel = apps.get_model('financas', 'ContaFinanceira')
            except LookupError:
                return

        if usuario:
            # --- Passo A: Buscar TODAS as contas válidas (Sem Combustível) ---
            # Se for admin vê tudo, se não, vê só as dele.
            if usuario.is_superuser:
                qs_contas = ContaModel.objects.all()
            else:
                qs_contas = ContaModel.objects.filter(usuario=usuario)

            # Exclui contas de Combustível (Regra de Negócio)
            qs_contas = qs_contas.exclude(
                Q(nome__icontains='Combustivel') | 
                Q(nome__icontains='Combustível')
            ).select_related('usuario')
            
            # Ordena por Usuário -> Nome da Conta
            qs_contas = qs_contas.order_by('usuario__username', 'nome')

            # --- Passo B: Popula o campo 'conta' com TUDO ---
            # O JavaScript vai se encarregar de esconder o que não precisa.
            # Colocamos o prefixo "USUARIO - " para o JS conseguir ler e filtrar.
            self.fields['conta'].queryset = qs_contas
            self.fields['conta'].label_from_instance = lambda obj: f"{obj.usuario.username.upper()} - {obj.nome}"

            # --- Passo C: Popula o campo 'filtro_usuario' ---
            # Pega os IDs únicos dos usuários donos dessas contas
            user_ids = qs_contas.values_list('usuario_id', flat=True).distinct()
            users_com_conta = User.objects.filter(id__in=user_ids).order_by('username')
            
            # Cria as opções: [TODOS] + [Lista de Usuários]
            opcoes_filtro = [('TODOS', 'Todos os Usuários')]
            for u in users_com_conta:
                opcoes_filtro.append((u.username.upper(), u.username.upper())) # Value = Nome (para facilitar o JS)
            
            self.fields['filtro_usuario'].choices = opcoes_filtro
            
            # Se não for admin, esconde o filtro ou deixa pré-selecionado ele mesmo
            if not usuario.is_superuser:
                self.fields['filtro_usuario'].initial = usuario.username.upper()
                # Opcional: Desabilitar o campo se quiser forçar
                # self.fields['filtro_usuario'].widget.attrs['disabled'] = True 
        else:
            self.fields['conta'].queryset = ContaModel.objects.none()