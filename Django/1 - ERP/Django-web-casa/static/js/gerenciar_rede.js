$(document).ready(function() {
    console.log("Script de Gerenciamento de Rede Carregado.");

    // ==========================================
    // 1. INICIALIZA DATATABLE (O QUE ESTAVA FALTANDO)
    // ==========================================
    if ($('#tabela-rede').length > 0) {
        $('#tabela-rede').DataTable({
            "language": {
                "url": "https://cdn.datatables.net/plug-ins/1.13.7/i18n/pt-BR.json"
            },
            "order": [[ 0, "asc" ]], // Ordena por Usuário (Coluna 0)
            "pageLength": 25,        // Mostra 25 itens por vez
            "autoWidth": false,      // Responsivo
            "stateSave": true,       // Lembra a página/busca ao recarregar
            "columnDefs": [
                { "orderable": false, "targets": 5 } // Desabilita ordenação na coluna Ações
            ]
        });
    }

    // Função auxiliar para pegar o CSRF Token
    const getCsrfToken = () => {
        const tokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
        return tokenInput ? tokenInput.value : '';
    };

    // ==========================================
    // 2. AJAX SALVAR DISPOSITIVO
    // ==========================================
    $('#formDispositivo').on('submit', function(e){
        e.preventDefault();
        
        // Instância do Modal Bootstrap 5
        const modalEl = document.getElementById('modalDispositivo');
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);

        $.ajax({
            url: $(this).attr('action'),
            type: 'POST',
            data: $(this).serialize(),
            success: function(res) {
                modal.hide();
                Swal.fire({
                    icon: 'success',
                    title: 'Sucesso!',
                    text: res.message,
                    showConfirmButton: false,
                    timer: 1500
                }).then(() => {
                    location.reload(); 
                });
            },
            error: function(xhr) {
                let msg = "Verifique os dados.";
                if(xhr.responseJSON && xhr.responseJSON.errors) {
                    msg = JSON.stringify(xhr.responseJSON.errors).replace(/[{}"]/g, '').replace(/\[|\]/g, '');
                }
                Swal.fire({ icon: 'error', title: 'Erro ao cadastrar', text: msg });
            }
        });
    });

    // ==========================================
    // 3. AJAX BLOQUEAR/LIBERAR
    // ==========================================
    $(document).on('click', '.btn-toggle-block', function(){
        const id = $(this).data('id');
        const btn = $(this);
        
        btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i>');

        $.ajax({
            url: `/rede/bloquear/${id}/`, 
            type: 'POST', 
            headers: {'X-CSRFToken': getCsrfToken()},
            success: function(res) {
                const Toast = Swal.mixin({
                    toast: true,
                    position: 'top-end',
                    showConfirmButton: false,
                    timer: 2000,
                    timerProgressBar: true
                });
                
                Toast.fire({
                    icon: 'success',
                    title: res.message
                }).then(() => {
                     location.reload();
                });
            },
            error: function() {
                Swal.fire('Erro', 'Não foi possível alterar o status.', 'error');
                btn.prop('disabled', false).html('<i class="fas fa-ban"></i> Erro');
            }
        });
    });
    
    // ==========================================
    // 4. AJAX EXCLUIR
    // ==========================================
    $(document).on('click', '.btn-excluir', function(){
        const id = $(this).data('id');
        
        Swal.fire({
            title: 'Tem certeza?',
            text: "O dispositivo e o histórico serão removidos.",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#d33',
            cancelButtonColor: '#6c757d',
            confirmButtonText: 'Sim, remover',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                $.ajax({
                    url: `/rede/excluir/${id}/`, 
                    type: 'POST', 
                    headers: {'X-CSRFToken': getCsrfToken()},
                    success: function(res) {
                        Swal.fire('Excluído!', '', 'success').then(() => { location.reload(); });
                    },
                    error: function() {
                        Swal.fire('Erro', 'Não foi possível excluir.', 'error');
                    }
                });
            }
        });
    });
    
    // ==========================================
    // 5. MÁSCARA MAC ADDRESS
    // ==========================================
    $('input[name="mac_address"]').on('input', function(){
        let v = $(this).val().replace(/[^0-9a-fA-F]/g, '').toUpperCase();
        let formatted = '';
        for(let i=0; i<v.length && i<12; i++) {
            if(i>0 && i%2==0) formatted += ':';
            formatted += v[i];
        }
        $(this).val(formatted);
    });
});