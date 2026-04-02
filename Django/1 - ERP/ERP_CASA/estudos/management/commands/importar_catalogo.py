import os
import re
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from estudos.models import AreaConhecimento, Especialidade, Curso, ModuloCurso, Aula

class Command(BaseCommand):
    help = 'Importação Inteligente: Limpa números (001 - Aula) e organiza pastas'

    def limpar_e_ordenar(self, texto_bruto):
        """
        Entrada: "002- 1 - Aula Teórica.mp4"
        Saída: (2, "Aula Teórica")
        """
        # Remove extensão se houver
        texto = os.path.splitext(texto_bruto)[0]
        
        # 1. Tenta extrair a ordem (primeiro número que aparece no começo)
        ordem = 99
        match_ordem = re.search(r'^(\d+)', texto)
        if match_ordem:
            ordem = int(match_ordem.group(1))
            
        # 2. Limpa o título (Remove números, traços, pontos e espaços do início)
        # Ex: "004 - 3 - Unhas" vira "Unhas"
        # O padrão abaixo diz: "No começo (^), pegue qualquer combinação de dígitos, espaços, traços ou pontos e apague"
        titulo_limpo = re.sub(r'^[\d\s\.\-_]+', '', texto)
        
        # Se a limpeza apagou tudo (ex: nome era só "01"), volta o original
        if not titulo_limpo.strip():
            titulo_limpo = texto

        return ordem, titulo_limpo.strip()

    def handle(self, *args, **options):
        base_dir = os.path.join(settings.MEDIA_ROOT, 'catalogo')

        if not os.path.exists(base_dir):
            self.stdout.write(self.style.ERROR(f"Pasta não encontrada: {base_dir}"))
            return

        self.stdout.write(self.style.WARNING(f"--- REFAZENDO CATÁLOGO (LIMPEZA DE NOMES) ---"))

        # Extensões válidas
        extensoes = ('.mp4', '.mkv', '.avi', '.mov', '.webm', '.ts', '.m4v', '.mpg', '.mpeg')
        ignorar = ('thumbs.db', '.ds_store', 'desktop.ini', '$recycle.bin')

        total_aulas = 0

        with transaction.atomic():
            # Cria Área Padrão
            area, _ = AreaConhecimento.objects.get_or_create(nome="Meus Cursos")

            # 1. CURSOS
            for nome_curso_fs in sorted(os.listdir(base_dir)):
                path_curso = os.path.join(base_dir, nome_curso_fs)
                if not os.path.isdir(path_curso) or nome_curso_fs.lower() in ignorar: continue

                # Limpa nome do curso também
                _, titulo_curso = self.limpar_e_ordenar(nome_curso_fs)
                
                self.stdout.write(self.style.MIGRATE_HEADING(f"Processando: {titulo_curso}"))

                espec, _ = Especialidade.objects.get_or_create(nome=titulo_curso, defaults={'area': area})
                curso, _ = Curso.objects.get_or_create(titulo=titulo_curso, defaults={'especialidade': espec})

                # 2. MÓDULOS (Aqui acontece a mágica da mesclagem)
                # Se tiver duas pastas "004 - Unhas" e "004 - 3 - Unhas", ambas viram "Unhas" e os vídeos são somados
                for nome_modulo_fs in sorted(os.listdir(path_curso)):
                    path_modulo = os.path.join(path_curso, nome_modulo_fs)
                    if not os.path.isdir(path_modulo) or nome_modulo_fs.lower() in ignorar: continue

                    ordem_mod, titulo_mod = self.limpar_e_ordenar(nome_modulo_fs)

                    modulo, _ = ModuloCurso.objects.get_or_create(
                        curso=curso,
                        titulo=titulo_mod, # O título limpo é a chave única agora
                        defaults={'ordem': ordem_mod}
                    )

                    # 3. AULAS (Busca Profunda)
                    # Conta quantas aulas esse módulo JÁ TEM para continuar a numeração se for pasta duplicada
                    contador_aulas = Aula.objects.filter(modulo=modulo).count() + 1
                    
                    for root, dirs, files in os.walk(path_modulo):
                        for arquivo_fs in sorted(files):
                            if arquivo_fs.lower().endswith(extensoes):
                                _, titulo_aula = self.limpar_e_ordenar(arquivo_fs)
                                path_rel = os.path.relpath(os.path.join(root, arquivo_fs), settings.MEDIA_ROOT)

                                # Evita duplicar o MESMO arquivo
                                if not Aula.objects.filter(modulo=modulo, video_arquivo=path_rel).exists():
                                    Aula.objects.create(
                                        modulo=modulo,
                                        titulo=titulo_aula,
                                        ordem=contador_aulas,
                                        video_arquivo=path_rel
                                    )
                                    # self.stdout.write(f"   [{titulo_mod}] + {titulo_aula}")
                                    total_aulas += 1
                                    contador_aulas += 1

        self.stdout.write(self.style.SUCCESS(f"\n--- SUCESSO: {total_aulas} AULAS PROCESSADAS ---"))