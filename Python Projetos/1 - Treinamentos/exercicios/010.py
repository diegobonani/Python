#CONVERTER MOEDAS POR DIEGO BONANI

op = int(input("1 - REAL, 2- DOLAR, 3- EURO"))
if(op == 1):
    moeda = float(input("Digite quanto quer saber em real"))
    print("{} r$ equivalem a {}$ e {}eur".format(moeda, moeda / 5.46, moeda / 6.65))
elif(op == 2):
    moeda = float(input("Digite quanto quer saber em Dolar"))
    print("{} $ equivalem a {}R$ e {}eur".format(moeda, moeda * 5.46, moeda / 0.82))
elif(op == 3):
    moeda = float(input("Digite quanto quer saber em Euro"))
    print("{}eur equivalem a {}R$ e {}$".format(moeda, moeda * 6.65, moeda * 1.22))
else:
    print("Comando inválido")