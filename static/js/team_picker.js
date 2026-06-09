(function () {
  function initTeamPicker(root) {
    var searchInput = root.querySelector('[data-team-picker-search]');
    var groupButtons = root.querySelectorAll('[data-group-filter]');
    var options = root.querySelectorAll('.team-picker-option');
    var emptyState = root.querySelector('[data-team-picker-empty]');
    var selectionValue = root.querySelector('[data-team-picker-selection-value]');
    var activeGroup = '';

    function updateSelection() {
      if (!selectionValue) {
        return;
      }
      var checked = root.querySelector('.team-picker-input:checked');
      if (!checked) {
        selectionValue.textContent = 'No preference';
        return;
      }
      var option = checked.closest('.team-picker-option');
      var label = option ? option.querySelector('.team-picker-label') : null;
      selectionValue.textContent = label ? label.textContent.trim() : 'No preference';
    }

    function applyFilters() {
      var query = searchInput ? searchInput.value.trim().toLowerCase() : '';
      var visibleCount = 0;

      options.forEach(function (option) {
        var teamName = option.dataset.teamName || '';
        var groupLetter = option.dataset.groupLetter || '';
        var matchesSearch = !query || teamName.indexOf(query) !== -1;
        var matchesGroup = !activeGroup || groupLetter === activeGroup;
        var visible = matchesSearch && matchesGroup;
        option.classList.toggle('d-none', !visible);
        if (visible) {
          visibleCount += 1;
        }
      });

      if (emptyState) {
        emptyState.classList.toggle('d-none', visibleCount > 0);
      }
    }

    if (searchInput) {
      searchInput.addEventListener('input', applyFilters);
    }

    groupButtons.forEach(function (button) {
      button.addEventListener('click', function () {
        activeGroup = button.dataset.groupFilter || '';
        groupButtons.forEach(function (item) {
          var isActive = item === button;
          item.classList.toggle('is-active', isActive);
          item.setAttribute('aria-pressed', isActive ? 'true' : 'false');
        });
        applyFilters();
      });
    });

    root.querySelectorAll('.team-picker-input').forEach(function (input) {
      input.addEventListener('change', updateSelection);
    });

    updateSelection();
    applyFilters();
  }

  function initAiPredictPanel(root) {
    var input = root.querySelector('.ai-predict-switch-input');
    var stateLabel = root.querySelector('[data-ai-predict-state]');
    if (!input) {
      return;
    }

    function syncState() {
      root.classList.toggle('ai-predict-panel-on', input.checked);
      if (stateLabel) {
        stateLabel.textContent = input.checked ? 'ON' : 'OFF';
      }
    }

    input.addEventListener('change', syncState);
    syncState();
  }

  document.querySelectorAll('[data-team-picker]').forEach(initTeamPicker);
  document.querySelectorAll('[data-ai-predict-panel]').forEach(initAiPredictPanel);
})();
