(function($) {
  $(function() {
    const el = $("#id_expense_by_combined");
    if (!el.length) return;

    el.prop("multiple", false);

    el.select2({
      width: "24%",
      placeholder: "Search Driver / Owner",
      allowClear: true,
      minimumInputLength: 1,
      ajax: {
        url: "/admin/operations/expense-by-autocomplete/",
        dataType: "json",
        delay: 250,
        data: function(params) {
          return { term: params.term };
        },
        processResults: function(data) {
          return data;
        }
      }
    });
  });
})(django.jQuery);
