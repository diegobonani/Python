#DESCOBERTA DA HIPOTENUSA COM O VALOR DE SENO, COSENO E TANGENTE POR DIEGO BONANI

import math 

ca = float(input("Digite o valor do Cateto Adjascente: "))
co = float(input("Digite o valor do Cateto Oposto: "))
hi = (ca ** 2 + co ** 2) ** 0.5

''' 
sen = math.sin(ca) # SENO DE UMA VARIAVEL
cos = math.cos(ca) # COS DE UMA VARIAVEL
tng = math.tan(ca) # TGT DE UMA VARIAVEL
'''

print("Cateto Adjascente: {} \n Cateto Oposto {} \n Hipotenusa {} ".format(ca,co,hi))