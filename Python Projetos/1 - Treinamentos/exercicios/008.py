#Conversão de medidas com opção por DIEGO BONANI

op = int(input("Digite a op 1- para CM 2- METROS 3-KM"))

try:
    if(op == 1):
        num = float(input("Digite a opção em CM"))
        print("A conversão de {} cm \n Metros {}m \n Km {}km".format(num, num / 100, num / 100000 ))
    elif(op == 2):
        num = float(input("Digite a opção em METROS"))
        print("A conversão de {}m \n Centimetros {} cm \n Km {}km" .format(num, num * 100, num / 1000 ))
    elif(op == 3):
        num = float(input("Digite a opção em KILOMETROS"))
        print("A conversão de {}km \n Centrimetros {} cm \n Metros{} m".format(num, num * 100000, num * 1000 ))
    else:
        print("Comando inválido")
except: 
    print("Deu erro")