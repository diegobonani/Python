(function($) {
    $(document).ready(function() {
        // Mapeia os campos do Django Admin (IDs padrões gerados pelo Django)
        var selectComodo = $('#id_comodo');
        var selectLocalizacao = $('#id_localizacao');

        // URL da sua view AJAX (verifique se bate com o urls.py)
        var urlAjax = "/estoque/ajax/load-localizacoes/";

        // Quando o cômodo mudar...
        selectComodo.change(function() {
            var comodoId = $(this).val();

            // Limpa as opções atuais da localização
            selectLocalizacao.html('<option value="">---------</option>');

            if (comodoId) {
                $.ajax({
                    url: urlAjax,
                    data: {
                        'comodo_id': comodoId
                    },
                    success: function(data) {
                        // Preenche com os novos dados recebidos
                        $.each(data, function(index, item) {
                            selectLocalizacao.append(
                                $('<option></option>').val(item.id).html(item.nome)
                            );
                        });
                    },
                    error: function(xhr, status, error) {
                        console.error("Erro ao carregar localizações: " + error);
                    }
                });
            }
        });
    });
})(django.jQuery);