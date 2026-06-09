(function () {
  var savedTimezone = document.body.dataset.userTimezone || '';
  var browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  var activeTimezone = savedTimezone || browserTimezone;
  var countdownElements = [];
  var pageReloadScheduled = false;

  var LOCALE_BY_TIMEZONE = {
    'Asia/Kolkata': 'en-IN',
    'Asia/Calcutta': 'en-IN',
  };

  var TIMEZONE_SHORT_LABELS = {
    'Asia/Kolkata': 'IST',
    'Asia/Calcutta': 'IST',
    'America/New_York': 'ET',
    'America/Chicago': 'CT',
    'America/Denver': 'MT',
    'America/Los_Angeles': 'PT',
    'Europe/London': 'GMT',
    'Europe/Paris': 'CET',
    'Europe/Berlin': 'CET',
    'Asia/Dubai': 'GST',
    'Asia/Singapore': 'SGT',
    'Asia/Tokyo': 'JST',
    'Asia/Seoul': 'KST',
    'Australia/Sydney': 'AEST',
    'Pacific/Auckland': 'NZST',
    'UTC': 'UTC',
  };

  if (!savedTimezone && browserTimezone) {
    document.cookie = (
      'django_timezone=' + encodeURIComponent(browserTimezone) +
      ';path=/;max-age=31536000;SameSite=Lax'
    );
  }

  function displayLocale() {
    return LOCALE_BY_TIMEZONE[activeTimezone];
  }

  function localeOptions(extra) {
    var options = Object.assign({}, extra || {});
    if (activeTimezone) {
      options.timeZone = activeTimezone;
    }
    return options;
  }

  function intlFormatter(extra) {
    return new Intl.DateTimeFormat(displayLocale(), localeOptions(extra));
  }

  function timezoneAbbreviation(date) {
    if (TIMEZONE_SHORT_LABELS[activeTimezone]) {
      return TIMEZONE_SHORT_LABELS[activeTimezone];
    }

    var parts = intlFormatter({ timeZoneName: 'short' }).formatToParts(date);
    var tzPart = parts.find(function (part) {
      return part.type === 'timeZoneName';
    });
    return tzPart ? tzPart.value : '';
  }

  function formatMatchRow(date) {
    var weekday = intlFormatter({ weekday: 'short' }).format(date);
    var monthDay = intlFormatter({ month: 'short', day: 'numeric' }).format(date);
    var time = intlFormatter({
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).format(date);
    var tz = timezoneAbbreviation(date);
    return weekday + ', ' + monthDay + ' · ' + time + (tz ? ' ' + tz : '');
  }

  function formatDetail(date) {
    var datePart = intlFormatter({
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(date);
    var time = intlFormatter({
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).format(date);
    var tz = timezoneAbbreviation(date);
    return datePart + ' ' + time + (tz ? ' ' + tz : '');
  }

  var formatters = {
    'match-row': formatMatchRow,
    detail: formatDetail,
  };

  function parseKickoffMs(el) {
    if (el.dataset.kickoffAt) {
      return parseFloat(el.dataset.kickoffAt) * 1000;
    }
    if (el.dataset.kickoff) {
      return new Date(el.dataset.kickoff).getTime();
    }
    return NaN;
  }

  function hidePredictActions(container) {
    if (!container) {
      return;
    }
    var actions = container.querySelector('.match-list-toolbar-actions');
    if (actions) {
      actions.classList.add('match-list-predictions-closed');
    }
    container.querySelectorAll('.match-list-predict-btn').forEach(function (button) {
      button.setAttribute('hidden', 'hidden');
      button.classList.add('d-none');
    });
  }

  function showKickoffClosed(el) {
    el.textContent = el.dataset.closedLabel || 'Started';
    el.classList.add('closed');
    el.dataset.kickoffClosed = '1';
    hidePredictActions(el.closest('.match-list-row'));
  }

  function schedulePageReload(delayMs) {
    if (pageReloadScheduled) {
      return;
    }
    pageReloadScheduled = true;
    window.setTimeout(function () {
      window.location.reload();
    }, delayMs || 300);
  }

  function handleKickoffExpired(el) {
    showKickoffClosed(el);

    if (el.dataset.autoSubmit) {
      var form = document.querySelector(el.dataset.autoSubmit);
      if (form && form.dataset.kickoffSubmitted !== '1') {
        form.dataset.kickoffSubmitted = '1';
        form.submit();
      }
      schedulePageReload(500);
      return;
    }

    schedulePageReload(300);
  }

  function formatCountdown(diff) {
    var h = Math.floor(diff / 3600000);
    var m = Math.floor((diff % 3600000) / 60000);
    var s = Math.floor((diff % 60000) / 1000);
    return h + 'h ' + m + 'm ' + s + 's';
  }

  function tickCountdown(el) {
    var kickoffMs = parseKickoffMs(el);
    if (isNaN(kickoffMs)) {
      el.textContent = '—';
      return;
    }

    var diff = kickoffMs - Date.now();
    if (diff <= 0) {
      if (el.dataset.kickoffClosed === '1') {
        return;
      }
      if (el.dataset.kickoffWasOpen === '1') {
        handleKickoffExpired(el);
      } else {
        showKickoffClosed(el);
      }
      return;
    }

    el.dataset.kickoffWasOpen = '1';
    el.textContent = formatCountdown(diff);
  }

  function startCountdown(el) {
    var kickoffMs = parseKickoffMs(el);
    if (isNaN(kickoffMs)) {
      el.textContent = '—';
      return;
    }

    countdownElements.push(el);
    tickCountdown(el);

    if (el.dataset.kickoffClosed === '1') {
      return;
    }

    window.setInterval(function () {
      tickCountdown(el);
    }, 1000);
  }

  function refreshAllCountdowns() {
    countdownElements.forEach(tickCountdown);
  }

  document.querySelectorAll('time.local-datetime').forEach(function (el) {
    var iso = el.getAttribute('datetime');
    if (!iso) {
      return;
    }
    var date = new Date(iso);
    if (isNaN(date.getTime())) {
      return;
    }
    var formatKey = el.dataset.format || 'match-row';
    var formatter = formatters[formatKey];
    el.textContent = formatter ? formatter(date) : intlFormatter().format(date);
    el.setAttribute('title', intlFormatter({ timeZoneName: 'long' }).format(date));
  });

  document.querySelectorAll('[data-timezone-label]').forEach(function (el) {
    var tz = timezoneAbbreviation(new Date());
    el.textContent = tz ? 'Kickoffs in ' + tz : 'Kickoffs in your local time';
  });

  document.querySelectorAll('[data-kickoff-at], [data-kickoff]').forEach(startCountdown);

  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible') {
      refreshAllCountdowns();
    }
  });
})();
