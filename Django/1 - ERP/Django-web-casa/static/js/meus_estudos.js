// Em: static/js/meus_estudos.js

$(document).ready(function() {
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

    // Inicializa os modais
    var modalAddMateria = new bootstrap.Modal(document.getElementById('modalAddMateria'));
    var modalAddNota = new bootstrap.Modal(document.getElementById('modalAddNota'));
    var modalExcluir = new bootstrap.Modal(document.getElementById('modalExcluirEstudo'));

    // --- 1. ADICIONAR MATÉRIA ---
    $('#formAddMateria').on('submit', function(e) {
        e.preventDefault();
        var form = $(this);
        var errorDiv = form.find('#form-errors-materia');
        errorDiv.hide().empty();

        $.ajax({
            type: 'POST',
            url: window.URL_ADD_MATERIA,
            data: form.serialize(),
            success: function(response) {
                if (response.success) {
                    modalAddMateria.hide();
                    location.reload(); // Simplesmente recarrega a página
                }
            },
            error: function(xhr) {
                var response = xhr.responseJSON;
                var msg = response.message || 'Verifique os campos.';
                errorDiv.html(msg).show();
            }
        });
    });

    // --- 2. ADICIONAR NOTA ---
    $('#formAddNota').on('submit', function(e) {
        e.preventDefault();
        var form = $(this);
        var errorDiv = form.find('#form-errors-nota');
        errorDiv.hide().empty();

        $.ajax({
            type: 'POST',
            url: window.URL_ADD_NOTA,
            data: form.serialize(),
            success: function(response) {
                if (response.success) {
                    modalAddNota.hide();
                    location.reload(); // Recarrega a página para mostrar a nova nota
                }
            },
            error: function(xhr) {
                var response = xhr.responseJSON;
                var errorMessage = 'Ocorreu um erro.';
                if (response && response.errors) {
                    errorMessage = '';
                    var errors = JSON.parse(response.errors);
                    for (var field in errors) {
                        errorMessage += `<p class="mb-1">${errors[field][0].message}</p>`;
                    }
                }
                errorDiv.html(errorMessage).show();
            }
        });
    });
    
    // --- 3. DELETAR MATÉRIA ---
    $('.btn-deletar-materia').on('click', function() {
        var pk = $(this).data('id');
        var nome = $(this).data('nome');
        
        $('#excluirEstudoTitle').text('Excluir Matéria');
        $('#excluirEstudoText').text(`Tem certeza que deseja excluir a matéria "${nome}"? Todas as notas associadas a ela também serão perdidas.`);
        $('#formExcluirEstudo').attr('action', window.URL_DELETAR_MATERIA.replace('0', pk));
        
        modalExcluir.show();
    });
    
    // --- 4. DELETAR NOTA ---
    $('.btn-deletar-nota').on('click', function() {
        var pk = $(this).data('id');
        
        $('#excluirEstudoTitle').text('Excluir Nota');
        $('#excluirEstudoText').text('Tem certeza que deseja excluir esta nota?');
        $('#formExcluirEstudo').attr('action', window.URL_DELETAR_NOTA.replace('0', pk));
        
        modalExcluir.show();
    });

    // --- 5. CONFIRMAR EXCLUSÃO (Genérico) ---
    $('#formExcluirEstudo').on('submit', function(e) {
        e.preventDefault();
        var form = $(this);

        $.ajax({
            type: 'POST',
            url: form.attr('action'),
            data: form.serialize(), // Envia o CSRF token
            success: function(response) {
                if (response.success) {
                    modalExcluir.hide();
                    location.reload(); // Recarrega a página
                } else {
                    alert('Erro: ' + response.message);
                }
            },
            error: function() {
                alert('Erro de conexão ao tentar excluir.');
            }
        });
    });
});