from django.core.management.base import BaseCommand
from usuarios.models import Perfil
from estudos.models import Matricula, DiarioBordo, Disciplina

class Command(BaseCommand):
    help = 'Cria dados de teste para validar o Painel'

    def handle(self, *args, **kwargs):
        # Pega o primeiro aluno que encontrar
        aluno = Perfil.objects.filter(esta_estudando=True).first()
        
        if not aluno:
            self.stdout.write(self.style.ERROR("Nenhum aluno encontrado! Cadastre um perfil primeiro."))
            return

        self.stdout.write(f"--- CRIANDO DADOS FAKE PARA: {aluno.nome_completo} ---")

        # 1. Cria Matrícula 2025 (CORREÇÃO: 'nivel_atual' agora é 'F1')
        matricula, created = Matricula.objects.get_or_create(
            aluno=aluno,
            ano_letivo=2025,
            defaults={'ano_serie_atual': 5, 'nivel_atual': 'F1'} 
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS("✔ Matrícula 2025 criada."))
        else:
            self.stdout.write(self.style.WARNING("! Matrícula 2025 já existia."))

        # 2. Cria 3 Matérias e Notas
        materias = ['Matemática Teste', 'Português Teste', 'Ciências Teste']
        
        for nome_mat in materias:
            # Cria a disciplina vinculada ao usuário
            disc, _ = Disciplina.objects.get_or_create(
                nome=nome_mat,
                usuario=aluno.usuario, 
                defaults={'categoria': 'ESCOLA'}
            )
            
            # Lança notas aleatórias
            DiarioBordo.objects.update_or_create(
                matricula=matricula,
                disciplina_base=disc,
                defaults={
                    'nota_1_bim': 8.5,
                    'nota_2_bim': 7.0,
                    'nota_3_bim': 9.2,
                    'nota_4_bim': None, 
                    'total_faltas': 2
                }
            )
            self.stdout.write(f"✔ Notas lançadas para: {nome_mat}")

        self.stdout.write(self.style.SUCCESS("\nCONCLUÍDO! Vá no painel, filtre por 2025 e veja se apareceu."))