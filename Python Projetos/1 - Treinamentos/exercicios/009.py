'''

#TABUADA V1 POR DIEGO BONANI

tab = int(input("Digite a tabuada que quer saber"))
print("{} . {} = {}".format(tab, 0, tab * 0))
print("{} . {} = {}".format(tab, 1, tab * 1))
print("{} . {} = {}".format(tab, 2, tab * 0))
print("{} . {} = {}".format(tab, 3, tab * 3))
print("{} . {} = {}".format(tab, 4, tab * 4))
print("{} . {} = {}".format(tab, 5, tab * 5))
print("{} . {} = {}".format(tab, 6, tab * 6))
print("{} . {} = {}".format(tab, 7, tab * 7))
print("{} . {} = {}".format(tab, 8, tab * 8))
print("{} . {} = {}".format(tab, 9, tab * 9))
print("{} . {} = {}".format(tab, 10, tab * 10))

#TABUADA V2 POR DIEGO BONANI

t = 0
tab = int(input("Digite a Tabuada que quer saber"))
while(t <= 10):
    t = t + 1 
    print("{} . {} = {}".format(tab, t, tab * t))

#TABUADA V3 POR DIEGO BONANI

tab = int(input("Digite a tabuada que quer saber"))
for t in range(0,11):
    print("{} . {} = {}".format(tab, t, tab * t))

#TABUADA V4 POR DIEGO BONANI

for i in range(0,11):
    for t in range(0,11):
        print("{} . {} = {}".format(i, t, i * t))

'''