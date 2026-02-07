#CALCULO DE DESCONTOS PARA EMPRESAS POR DIEGO BONANI V1 
#V2 - PODERIA ADICIONAR UM VETOR PARA CLASSIFICAR POR SETOR

qnt_funcionarios = int(input("Digite quantos funcionarios tem"))
try:
    if qnt_funcionarios >= 1000 and qnt_funcionarios < 3000:
        sal = float(input("Digite o salário dos funcionários"))
        desc = sal * 0.05
        print("O salário obtido de {}R$ terá um desconto de {}R$, totalizando {}R$".format(sal,desc, sal - desc))
    elif qnt_funcionarios >= 3000 and qnt_funcionarios < 5000:
        sal = float(input("Digite o salário dos funcionários"))
        desc = sal * 0.10
        print("O salário obtido de {}R$ terá um desconto de {}R$, totalizando {}R$".format(sal,desc, sal - desc))
    elif qnt_funcionarios >= 5000:
        sal = float(input("Digite o salário dos funcionários"))
        desc = sal * 0.15
        print("O salário obtido de {}R$ terá um desconto de {}R$, totalizando {}R$".format(sal,desc, sal - desc))
    else:
        print("Não encontrado")
except: 
    print("Operação inválida")