from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Manutencao
# Importamos os modelos de Finanças para fazer a integração
from financas.models import Financa, FinancaCategoria, ContaFinanceira

@receiver(post_save, sender=Manutencao)
def integrar_manutencao_financeiro_e_veiculo(sender, instance, created, **kwargs):
    """
    Automatização tripla ao salvar uma Manutenção:
    1. Atualiza o KM do Veículo (se for maior que o atual).
    2. Atualiza o Catálogo de Serviços (ex: define a data da última troca de óleo).
    3. Cria ou Atualiza o Lançamento Financeiro (Despesa).
    """
    
    # --- 1. ATUALIZAÇÃO DO VEÍCULO (Odômetro) ---
    veiculo = instance.veiculo
    if instance.km_odometro > veiculo.km_atual:
        veiculo.km_atual = instance.km_odometro
        veiculo.save()

    # --- 2. ATUALIZAÇÃO DO CATÁLOGO DE SERVIÇOS ---
    # Se essa manutenção foi vinculada a um serviço preventivo (ex: Troca de Óleo)
    if instance.servico_realizado:
        servico = instance.servico_realizado
        # Atualiza o registro de quando foi feito pela última vez
        servico.ultima_km = instance.km_odometro
        servico.ultima_data = instance.data_servico
        servico.save()

    # --- 3. INTEGRAÇÃO FINANCEIRA ---
    
    # Define a categoria padrão para manutenções
    categoria, _ = FinancaCategoria.objects.get_or_create(
        nome="Manutenção Veicular",
        defaults={'tipo_custo': 'Variadas'} # Manutenção geralmente é custo variável
    )

    # Tenta encontrar uma conta padrão para debitar (Pega a primeira do usuário ou a compartilhada)
    # Idealmente, no futuro, você pode colocar um campo "conta_pagamento" no formulário de manutenção
    conta = ContaFinanceira.objects.filter(usuario=instance.usuario).first()
    
    # Se não tiver nenhuma conta cadastrada, não tem como lançar financeiro
    if not conta:
        return 

    descricao_lancamento = f"Manutenção {veiculo.modelo}: {instance.descricao}"

    if created:
        # --- CENÁRIO: CRIAR NOVA MANUTENÇÃO ---
        # Cria a despesa no app Finanças
        despesa = Financa.objects.create(
            conta=conta,
            usuario=instance.usuario,
            nome=descricao_lancamento,
            descricao=f"KM: {instance.km_odometro}",
            categoria=categoria,
            tipo='Despesas',
            valor=instance.custo_total,
            data_registro=instance.data_servico
        )
        
        # Salva o vínculo: A manutenção agora conhece sua despesa financeira
        instance.lancamento_financeiro = despesa
        instance.save()
        
    else:
        # --- CENÁRIO: EDITAR MANUTENÇÃO EXISTENTE ---
        # Se você editou o preço da peça no app Carro, atualiza no Financeiro
        if instance.lancamento_financeiro:
            despesa = instance.lancamento_financeiro
            despesa.valor = instance.custo_total
            despesa.nome = descricao_lancamento
            despesa.data_registro = instance.data_servico
            despesa.save()

@receiver(post_delete, sender=Manutencao)
def remover_manutencao_financeiro(sender, instance, **kwargs):
    """
    Se você excluir o registro de manutenção (foi erro de digitação, por exemplo),
    o sistema exclui automaticamente a despesa financeira associada para não furar o caixa.
    """
    if instance.lancamento_financeiro:
        instance.lancamento_financeiro.delete()