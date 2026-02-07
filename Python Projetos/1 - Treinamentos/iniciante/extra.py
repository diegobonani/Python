#LISTA DE EXERCICIO FEITO POR DIEGO BONANI
#FONTE: https://wiki.python.org.br/EstruturaSequencial

'''
 1. print("Olá mundo")

 2. num = eval(input("Digite um número"))
    print("O numero informado foi" , num)

 3. a = eval(input("Digite n1"))
    b = eval(input("Digite n2"))
    s = a + b
    print("A soma de {} + {} foi {}".format(a,b, s))

 4. n1 = eval(input("Digite a nota 1"))
    n2 = eval(input("Digite a nota 2"))
    n3 = eval(input("Digite a nota 3"))
    n4 = eval(input("Digite a nota 4"))
    r = (n1 + n2 + n3 + n4) / 4
    print("N1 FOI {} \n N2 {} \n N3 {} \n N4 {} \n e a media final foi de {}".format(n1,n2,n3,n4, r))

 5. e = int(input(" 1- CONVERTER CENTIMETRO PARA METRO \n 2- CONVERTER METRO PARA CENTIMETRO " ))
    if e == 1 :
        n1 = eval(input("Digite o valor em cm a ser convertido "))
        metro = n1 / 100
        print("O valor em {} cm foi convertido para {}m".format(n1, metro))
    elif e== 2:
        n1 = eval(input("Digite o valor de metro para converter a cm"))
        centimetro = n1 * 100
        print("O valor em {} m foi convertido para {}cm".format(n1, centimetro))
    else:
        print("Valor não encontrado")

 6. pi = 3.1456
    raio = eval(input("Digite o raio do circulo"))
    area = pi * (raio ** 2)
    print("O raio de {}cm definido \n pela área {}cm".format(raio,area))

 7. area = eval(input("Digite a área do quadrado")) ** 2
    dobro = area * 2
    print("A area do quadrado é de {} \n seu dobro é {}cm ".format(area, dobro))

 8. salHora = eval("Digite quanto que você ganha por hora")
    nMes = eval("Quanto tempo trabalhou no mes?")
    salario = salHora * nMes

 9. #C = 5 * ((F-32) / 9).

    F = eval(input("Digite o valor do Grau em farehint"))
    Aux1 = F - 32
    Aux2 = Aux1 / 9
    c = Aux2 * 5
    print("O valor do graus em CELSIUS é {}".format(c))

 10. c = eval(input("Digite o valor do Grau em Celsius"))
    aux1 = c / 1.8
    f = aux1 + 32
    print("O valor do graus em FAREHINT é {}".format(f))

 11. n1 = int(input("Digite um inteiro 1"))
    n2 = int(input("Digite um inteiro 2"))
    n3 = float(input("Digite um real 3"))

    a =  (n1 * 2)  * (n2 * 0.5)
    b = (n1 * 3) + n3
    c =  n3 ** 3

    print("{} {} {} {} {} {}".format(n1,n2,n3,a,b,c))

  12. alt = eval(input("Digite sua altura"))
      imc = 72.7 * alt - 58
      print("O seu peso ideal é {}kg".format(imc))

  13. alt = eval(input("Digite sua altura"))
      imc = 72.7 * alt - 58
      print("O seu peso ideal é {}kg".format(imc))

      alt = eval(input("Digite sua altura"))
      imc = 62.1 * alt - 44.7
      print("O seu peso ideal é {}kg".format(imc))

  14. peso = eval(input("Digite o peso de peixe pescados"))
        excesso = peso - 50
        multa = excesso * 4
        if excesso > 0 :
            print(excesso,multa)
        else:
            print("Não houve excesso portanto não haverá multa")

   15. l1 = eval(input("Digite o lado 1 da parede"))
        l2 = eval(input("Digite o lado 2 da parede"))
        area = l1 * l2
        tinta = area / 2
        print("A tinta necessária é de {}l \n A area da parede {}m".format(tinta,area))

15. # simulador de caixa

import math

retirada = eval(input("Valor do saque:"))
notas = [1,10,50]
n50 = retirada / notas[2]
notas50 = math.trunc(n50)
resto1 = retirada - (notas50 * 50)
while True:

16. ano = 2020
nome = input("Digite o seu nome")
#idade = int(input("Ano de Nascimento"))
n1 = eval(input("Nota 1"))
n2 = eval(input("Nota 2"))
idade = ano - int(input("Apresente sua data de nascimento"))
media = (n1 + n2 ) / 2
if media >= 6 and idade >= 18:
     print("Aprovado!" + nome)
elif media < 6 and idade >= 18:
     print("Reprovado!")
else:
     print("Não pode participar por ser menor de 18")

17. palavra = input('Digite uma palavra: ').lower().strip().replace(' ', '')
print(palavra[::-1])
if palavra == palavra[::-1]:
    print('É palíndromo')
else:
    print('Não é palíndromo')

18. fibonnaci
    anterior = 0
proximo = 0

while(proximo < 50):
    print(proximo)
    proximo = proximo + anterior
    anterior = proximo - anterior
    if(proximo == 0):
        proximo = proximo + 1

'''

'''
cont = 0
pessoas = 8
quantidadePessoas = []
try:
    if True:
        for x in range(1,pessoas):
            nome = str(input("Digite o nome da pessoa"))
            quantidadePessoas = quantidadePessoas.append(float(input("Digite o peso")))
            print(quantidadePessoas)
            if peso > 90:
                cont += 1
                media = somaPeso / x
                print("Adicionada com sucesso a {}a pessoa".format(x))
            elif peso != 90:
                diferentes = []
                diferentes.append(len(nome))
                print("{} Está abaixo do peso".format(diferentes.append(len(nome))))
except:
    print("Não foi")
    
cont = 0
num = int(input("Digite o N fatorial:"))
for i in range(1, num + 1):
'''

import json
from urllib import request
url = request.urlopen('http://ip-api.com/json').read()
jsn = json.loads(url.decode('UTF-8'))
print(jsn['query'])

