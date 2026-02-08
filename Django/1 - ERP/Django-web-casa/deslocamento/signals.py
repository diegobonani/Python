# deslocamento/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Abastecimento
from financas.models import Financa, FinancaCategoria, ContaFinanceira

@receiver(post_save, sender=Abastecimento)
def gerenciar_financeiro_abastecimento(sender, instance, created, **kwargs):
    """
    Sincroniza o Abastecimento com o Módulo Financeiro e Atualiza o Carro.
    """
    # 1. Atualiza KM do Carro
    if instance.km_odometro > instance.veiculo.km_atual:
        instance.veiculo.km_atual = instance.km_odometro
        instance.veiculo.save()

    # 2. Cria/Atualiza Lançamento Financeiro
    descricao = f"Abastecimento: {instance.veiculo.modelo} ({instance.litros}L {instance.get_tipo_combustivel_display()})"
    
    # Tenta achar categoria 'Combustível' ou cria uma padrão
    categoria, _ = FinancaCategoria.objects.get_or_create(
        nome="Combustível", 
        defaults={'tipo_custo': 'Variadas'}
    )
    
    # Pega uma conta padrão (Carteira ou a primeira que achar do usuário)
    conta = ContaFinanceira.objects.filter(usuario=instance.usuario).first()
    
    if not conta:
        return # Se não tiver conta, não lança financeiro (evita erro)

    if created:
        # Cria novo lançamento
        financa = Financa.objects.create(
            conta=conta,
            usuario=instance.usuario,
            nome=descricao,
            categoria=categoria,
            tipo='Despesas',
            valor=instance.valor_total,
            data_registro=instance.data
        )
        # Salva o vínculo no abastecimento
        instance.lancamento_financeiro = financa
        instance.save()
    
    else:
        # Se for edição, atualiza o lançamento existente
        if instance.lancamento_financeiro:
            f = instance.lancamento_financeiro
            f.valor = instance.valor_total
            f.nome = descricao
            f.data_registro = instance.data
            f.save()

@receiver(post_delete, sender=Abastecimento)
def apagar_financeiro_abastecimento(sender, instance, **kwargs):
    """Se apagar o abastecimento, apaga a despesa financeira."""
    if instance.lancamento_financeiro:
        instance.lancamento_financeiro.delete()