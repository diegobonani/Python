#tabuada feito por DIEGO BONANI

def mostraTabuada():

    #tab = int(input("Digite a tabuada que quer saber:"))
    for i in range(0,11):
       for t in range(0,11):
           print("{} x {} = {}".format(i, t, i *t ))

mostraTabuada()