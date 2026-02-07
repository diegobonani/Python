/**
 * GERENCIADOR DE ROTINAS - V2.0 FINAL
 */

$(document).ready(function() {
    "use strict";

    // CSRF Setup
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrftoken = getCookie('csrftoken');

    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    // 1. CHECKBOX DO USUÁRIO
    $('.check-status').on('change', function() {
        const checkbox = $(this);
        const id = checkbox.data('id');
        const isChecked = checkbox.is(':checked');
        const status = isChecked ? 'CONCLUIDO' : 'PENDENTE';
        const row = checkbox.closest('tr');

        // Optimistic UI
        if(isChecked) row.addClass('bg-opacity-10 bg-success');
        else row.removeClass('bg-opacity-10 bg-success');

        $.ajax({
            url: window.URLS_ROTINA.atualizarStatus + id + '/',
            type: 'GET',
            data: { 'status': status },
            success: function(res) {
                if(!res.success) {
                    alert('Erro ao atualizar.');
                    location.reload();
                } else {
                    console.log('Pontos atualizados:', res.pontos);
                }
            },
            error: function() {
                alert('Erro de conexão.');
                location.reload();
            }
        });
    });

    // 2. ADMIN ONLY
    if (window.IS_ADMIN) {
        
        // Modal de Edição (Martelinho)
        $('.btn-edit-admin').on('click', function() {
            const btn = $(this);
            const modalEl = document.getElementById('modalAdminEdit');
            const modal = new bootstrap.Modal(modalEl);
            
            $('#edit_tarefa_id').val(btn.data('id'));
            $('#edit_status').val(btn.data('status'));
            $('#edit_pontos').val(btn.data('pontos'));
            $('#edit_obs').val(btn.data('obs'));
            
            $('#formAdminEdit').attr('action', window.URLS_ROTINA.adminEditar + btn.data('id') + '/');
            modal.show();
        });

        $('#formAdminEdit').on('submit', function(e) {
            e.preventDefault();
            const form = $(this);
            $.ajax({
                type: 'POST',
                url: form.attr('action'),
                data: form.serialize(),
                success: function(res) {
                    if(res.success) location.reload();
                    else alert('Erro ao salvar.');
                }
            });
        });

        // Histórico no Modal de Castigo
        $('#id_castigo_usuario').on('change', function() {
            const userId = $(this).val();
            const $box = $('#box-ultimo-castigo');
            
            if (!userId) { $box.addClass('d-none'); return; }

            $.ajax({
                url: window.URLS_ROTINA.ultimoCastigo,
                data: { 'user_id': userId },
                success: function(data) {
                    if (data.existe) {
                        $('#hist-data').text(data.data);
                        $('#hist-motivo').text(data.motivo);
                        $('#hist-gravidade').text(data.gravidade);
                        $box.removeClass('d-none');
                    } else {
                        $box.addClass('d-none');
                    }
                }
            });
        });
    }
});