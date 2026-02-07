#Calculadora 1.0v por Diego Bonani

numA = int(input("Digite 1º número para conta"))
numB = int(input("Digite 2º número para conta"))
soma = numA + numB
sub = numA - numB
multi = numA * numB
div = numA / numB 
pot = numA ^ numB
resto = numA % numB
print("O resultado de {} com {} é: \n Soma: {}, Subtração {}, Multi {}, Div {}, Potencialização {} Resto {}".format(numA,numB, soma,sub,multi,div,pot,resto))
