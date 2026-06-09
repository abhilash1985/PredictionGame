(function () {
  var savedTimezone = document.body.dataset.userTimezone || '';
  var browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  var activeTimezone = savedTimezone || browserTimezone;

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

  function hidePredictActions(container) {
    if (!container) {
      return;
    }
    container.querySelectorAll('.match-list-predict-btn').forEach(function (button) {
      button.classList.add('d-none');
    });
  }

  function disablePredictForm(form) {
    if (!form) {
      return;
    }
    form.querySelectorAll('input, select, textarea, button').forEach(function (field) {
      field.disabled = true;
    });
  }

  function autoSubmitForm(selector) {
    if (!selector) {
      return;
    }
    var form = document.querySelector(selector);
    if (!form || form.dataset.kickoffSubmitted === '1') {
      return;
    }
    form.dataset.kickoffSubmitted = '1';
    disablePredictForm(form);
    if (typeof form.requestSubmit === 'function') {
      form.requestSubmit();
      return;
    }
    form.submit();
  }

  function handleKickoffClosed(el) {
    el.textContent = el.dataset.closedLabel || 'Started';
    el.classList.add('closed');
    hidePredictActions(el.closest('.match-list-row'));
    if (el.dataset.autoSubmit) {
      autoSubmitForm(el.dataset.autoSubmit);
    }
  }

  function formatCountdown(diff) {
    var h = Math.floor(diff / 3600000);
    var m = Math.floor((diff % 3600000) / 60000);
    var s = Math.floor((diff % 60000) / 1000);
    return h + 'h ' + m + 'm ' + s + 's';
  }

  function startCountdown(el) {
    var kickoff = new Date(el.dataset.kickoff);
    if (isNaN(kickoff.getTime())) {
      return;
    }

    function tick() {
      var diff = kickoff - new Date();
      if (diff <= 0) {
        if (el.dataset.kickoffClosed !== '1') {
          el.dataset.kickoffClosed = '1';
          handleKickoffClosed(el);
        }
        return;
      }
      el.textContent = formatCountdown(diff);
    }

    tick();
    setInterval(tick, 1000);
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

  document.querySelectorAll('[data-kickoff]').forEach(startCountdown);
})();
