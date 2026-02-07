#JOGO DE ADIVINHA FEITO POR: DIEGOBONANI

import random

vida = 10
vidasPerdidas = 0
rodada = 0
pontos = 0
nome = str(input("Digite seu nome"))
while True:
    while vidasPerdidas >= 0:
        while rodada >= 0 and vida != 0 and vidasPerdidas < 10:
            rodada += 1
            num = int(input("Digite um número"))
            embaralhar = random.randint(1,10)
            if embaralhar != num:
                vida -= 1
                vidasPerdidas += 1
                print("Você errou. Tem {} vidas".format(vida))
            elif embaralhar == num:
                pontos = pontos + 1000
                print("Parabéns, você acertou e está com {} pontos. Tem {} vidas".format(pontos,vida))
            if vida == 0:
                print("Fim de jogo! {} \n Você teve {} pontos".format(nome,pontos))
