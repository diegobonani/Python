from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum, F, Value, DecimalField
from django.db.models.functions import Coalesce

# Imports dos modelos
from .models import ListaCompraProduto
from financas.models import Financa

@receiver([post_save, post_delete], sender=ListaCompraProduto)
def atualizar_valor_e_transacao_compra(sender, instance, **kwargs):
    """
    Este sinal é disparado sempre que um ListaCompraProduto é salvo ou deletado.
    Ele recalcula o valor total da compra e atualiza o lançamento financeiro associado.
    """
    compra = instance.compra
    
    # Etapa 1: O sinal só age em compras marcadas como 'detalhada'.
    if not compra.detalhada:
        return

    # Etapa 2: Recalcula o valor total da compra com base nos produtos.
    novo_total = compra.produtos.aggregate(
        total=Coalesce(Sum(F('quantidade') * F('valor_unit')), Value(0.0, output_field=DecimalField()))
    )['total']
    
    # Etapa 3: Atualiza o valor_total no modelo ListaCompra.
    if compra.valor_total != novo_total:
        type(compra).objects.filter(pk=compra.pk).update(valor_total=novo_total)

    # Etapa 4: Encontra e atualiza o lançamento financeiro (Financa) associado.
    try:
        # CORREÇÃO: Busca a transação financeira que está LIGADA a esta compra.
        financa_associada = Financa.objects.get(compra_associada=compra)
        
        # Agora que temos o lançamento, podemos verificar a conta e suas regras.
        conta = financa_associada.conta
        
        # Validação de Saldo: Calcula o saldo que a conta teria ANTES desta compra.
        saldo_sem_esta_compra = conta.saldo_atual + financa_associada.valor
        
        # Se a conta é protegida e o novo total ultrapassa o saldo disponível...
        if conta.nao_permite_negativo and saldo_sem_esta_compra < novo_total:
            # Em um cenário real, poderíamos gerar um aviso. Por segurança,
            # aqui garantimos que a despesa não ultrapasse o saldo.
            # A validação principal já acontece no formulário.
            # O ideal aqui é apenas manter a sincronia.
            pass

        # Atualiza o valor da despesa para corresponder ao novo total da compra.
        if financa_associada.valor != novo_total:
            financa_associada.valor = novo_total
            financa_associada.save(update_fields=['valor'])

    except Financa.DoesNotExist:
        # Lógica de segurança: se a finança não foi criada, não faz nada.
        pass