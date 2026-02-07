$(document).ready(function() {
    // Inicializa os modais do Bootstrap 5
    const modalAdicionar = new bootstrap.Modal(document.getElementById('modalAdicionarPonto'));
    const modalEditar = new bootstrap.Modal(document.getElementById('modalEditarPonto'));
    const modalExcluir = new bootstrap.Modal(document.getElementById('modalExcluirPonto'));

    // =================================================================
    // 0. AÇÃO RÁPIDA - BATER PONTO (BOTÕES NO TOPO)
    // =================================================================
    $('.btn-bater-ponto').on('click', function() {
        const btn = $(this);
        const acao = btn.data('acao');
        // Guarda o HTML original para restaurar em caso de erro
        const originalHtml = btn.html();

        // Desabilita o botão para evitar duplo clique e mostra um spinner
        btn.prop('disabled', true).html('<div class="spinner-border spinner-border-sm" role="status"></div> Registrando...');

        $.ajax({
            type: 'POST',
            url: window.URL_BATER_PONTO, // Variável definida no template HTML
            data: {
                'acao': acao,
                // Pega o token CSRF do formulário oculto na página (se houver) ou do cookie
                'csrfmiddlewaretoken': document.querySelector('[name=csrfmiddlewaretoken]')?.value
            },
            success: function(response) {
                if (response.success) {
                    // Recarrega a página para atualizar tudo (botões, tabela e saldos)
                    window.location.reload();
                }
            },
            error: function(xhr) {
                const response = xhr.responseJSON;
                alert(response.message || 'Erro ao registrar ponto.');
                // Reabilita o botão e restaura o texto original em caso de erro
                btn.prop('disabled', false).html(originalHtml);
            }
        });
    });

    // =================================================================
    // 1. INICIALIZAÇÃO DO DATATABLE
    // =================================================================
    $('#tabelaMeusPontos').DataTable({
        language: {
            url: "https://cdn.datatables.net/plug-ins/2.0.8/i18n/pt-BR.json"
        },
        "order": [[ 0, "desc" ]], // Ordena pela Data (coluna 0) de forma decrescente
        "pageLength": 31, // Mostra até 31 dias por padrão
        "responsive": true,
        "columnDefs": [
            { "orderable": false, "targets": 9 } // Desabilita ordenação na coluna de "Ações"
        ]
    });

    // =================================================================
    // 2. ADICIONAR NOVO REGISTRO MANUALMENTE (MODAL)
    // =================================================================
    $('#formAdicionarPonto').on('submit', function(e) {
        e.preventDefault();
        const form = $(this);
        const errorDiv = form.find('#form-errors-add');
        
        errorDiv.hide().empty();

        $.ajax({
            type: 'POST',
            url: window.URL_REGISTRAR_PONTO,
            data: form.serialize(),
            success: function(response) {
                if (response.success) {
                    modalAdicionar.hide();
                    window.location.reload();
                }
            },
            error: function(xhr) {
                let errorMessage = 'Ocorreu um erro ao salvar.';
                const response = xhr.responseJSON;
                
                if (response) {
                    if (response.message) {
                        errorMessage = response.message;
                    } else if (response.errors) {
                        errorMessage = '<ul class="mb-0 text-start">';
                        let errors;
                        try { errors = (typeof response.errors === 'string') ? JSON.parse(response.errors) : response.errors; } catch (e) { errors = {}; }

                        for (const field in errors) {
                            errors[field].forEach(error => {
                                const fieldName = (field === '__all__') ? '' : `<strong>${field}:</strong> `;
                                errorMessage += `<li>${fieldName}${error.message}</li>`;
                            });
                        }
                        errorMessage += '</ul>';
                    }
                }
                errorDiv.html(errorMessage).show();
            }
        });
    });

    // =================================================================
    // 3. ABRIR MODAL DE EDIÇÃO (Carregar dados via AJAX)
    // =================================================================
    $('#tabelaMeusPontos').on('click', '.btn-editar-ponto', function() {
        const btn = $(this);
        const pk = btn.data('id');
        const form = $('#formEditarPonto');
        const errorDiv = form.find('#form-errors-edit');

        form[0].reset();
        errorDiv.hide().empty();

        // Define a URL de ação do formulário para o ID correto
        form.attr('action', window.URL_EDITAR_PONTO.replace('0', pk));

        // Busca os dados atuais do registro
        $.ajax({
            type: 'GET',
            url: window.URL_GET_PONTO_JSON.replace('0', pk),
            success: function(data) {
                form.find('[name="data"]').val(data.data);
                form.find('[name="entrada"]').val(data.entrada);
                form.find('[name="saida_almoco"]').val(data.saida_almoco);
                form.find('[name="retorno_almoco"]').val(data.retorno_almoco);
                form.find('[name="saida"]').val(data.saida);
                
                modalEditar.show();
            },
            error: function() {
                alert('Erro ao carregar os dados do registro. Tente recarregar a página.');
            }
        });
    });

    // =================================================================
    // 4. SALVAR EDIÇÃO (AJAX)
    // =================================================================
    $('#formEditarPonto').on('submit', function(e) {
        e.preventDefault();
        const form = $(this);
        const errorDiv = form.find('#form-errors-edit');
        
        errorDiv.hide().empty();

        $.ajax({
            type: 'POST',
            url: form.attr('action'),
            data: form.serialize(),
            success: function(response) {
                if (response.success) {
                    modalEditar.hide();
                    window.location.reload();
                }
            },
            error: function(xhr) {
                // (Mesma lógica de tratamento de erro do "Adicionar")
                let errorMessage = 'Ocorreu um erro ao salvar.';
                const response = xhr.responseJSON;
                if (response) {
                    if (response.message) {
                        errorMessage = response.message;
                    } else if (response.errors) {
                        errorMessage = '<ul class="mb-0 text-start">';
                        let errors;
                        try { errors = (typeof response.errors === 'string') ? JSON.parse(response.errors) : response.errors; } catch (e) { errors = {}; }
                        for (const field in errors) {
                            errors[field].forEach(error => {
                                const fieldName = (field === '__all__') ? '' : `<strong>${field}:</strong> `;
                                errorMessage += `<li>${fieldName}${error.message}</li>`;
                            });
                        }
                        errorMessage += '</ul>';
                    }
                }
                errorDiv.html(errorMessage).show();
            }
        });
    });

    // =================================================================
    // 5. EXCLUIR REGISTRO
    // =================================================================
    $('#tabelaMeusPontos').on('click', '.btn-deletar-ponto', function() {
        const pk = $(this).data('id');
        $('#formExcluirPonto').attr('action', window.URL_DELETAR_PONTO.replace('0', pk));
        modalExcluir.show();
    });

    $('#formExcluirPonto').on('submit', function(e) {
        e.preventDefault();
        const form = $(this);
        
        $.ajax({
            type: 'POST',
            url: form.attr('action'),
            data: form.serialize(),
            success: function(response) {
                if (response.success) {
                    modalExcluir.hide();
                    window.location.reload();
                }
            },
            error: function() {
                alert('Erro ao tentar excluir o registro.');
                modalExcluir.hide();
            }
        });
    });
});