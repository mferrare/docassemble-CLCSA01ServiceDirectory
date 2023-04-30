// add the font
$('head').append(
  $(
    '<link href="https://fonts.googleapis.com/css2?family=Josefin+Sans:ital,wght@0,300;0,400;0,600;0,700;1,300;1,400;1,600;1,700&family=Nunito:ital,wght@0,300;0,400;0,600;0,700;0,900;0,1000;1,300;1,400;1,600;1,700;1,900&family=Poppins:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;1,100;1,400;1,500;1,600;1,700;1,800&family=Raleway:ital,wght@0,400;0,500;0,700;1,400;1,500;1,700&family=Ubuntu:ital,wght@0,300;0,400;0,700;1,300;1,400;1,700&display=swap" rel="stylesheet">'
  )[0]
);

// add custom navbar and footer
$('body').prepend(
  '<nav id="CLCSA_navbar"><div id="CLCSA_navbar-container"><div id="CLCSA_logo"></div><div id="CLCSA_btns"></div></div></nav>'
);
$('#CLCSA_navbar #CLCSA_logo')
  .append($('#dapagetitle img')[0])
  .css('opacity', '0');
//  Place the Safe Exit button in the new nav
// get the exit button - the text inside `contains` should match `exit label`.
var escapeRef = $('#danavbar-collapse .nav-link:contains(Safe Exit)');
escapeRef.parents('.nav-item').remove(); // remove the `li` item for the exit button
escapeRef.removeClass('nav-link');
escapeRef.attr('id', 'escapeBtn');
escapeRef.addClass('btn btn-da DLL_btn-danger-text'); // add classes to make it look like a button
// check if the mobile nav has other items
if ($('#danavbar-collapse .navbar-nav').children().length == 0) {
  // the menu only has the exit button so remove it
  $('#danavbar-collapse').remove();
  $('#damobile-toggler').remove();
}
// add escape icon
let label = escapeRef.text();
escapeRef.text('');
escapeRef.append('<span>' + label + '</span>');
escapeRef.append(`<svg
width='19'
height='20'
viewBox='0 0 19 20'
fill='none'
xmlns='http://www.w3.org/2000/svg'
>
<path
  d='M11.5 7V3.25C11.5 2.65326 11.2629 2.08097 10.841 1.65901C10.419 1.23705 9.84674 1 9.25 1H3.25C2.65326 1 2.08097 1.23705 1.65901 1.65901C1.23705 2.08097 1 2.65326 1 3.25V16.75C1 17.3467 1.23705 17.919 1.65901 18.341C2.08097 18.7629 2.65326 19 3.25 19H9.25C9.84674 19 10.419 18.7629 10.841 18.341C11.2629 17.919 11.5 17.3467 11.5 16.75V13M14.5 13L17.5 10M17.5 10L14.5 7M17.5 10H4.75'
  stroke='currentColor'
  stroke-width='1.5'
  stroke-linecap='round'
  stroke-linejoin='round'
/>
</svg>`);
// add the button to the nav
$('#CLCSA_navbar #CLCSA_btns').append(escapeRef).css('opacity', '0');
// add the footer
$('body').append(
  $('#dabody footer').removeClass('dafooter').css('opacity', '0')[0]
);

// add the progress bar - we add it once and then update the value as we proceed
$('#CLCSA_navbar').after(
  '<div id="dll_mainSection" class="col-lg-10 container"></div>'
);
$('#dll_mainSection').append(
  '<div class="progress mt-2" role="progressbar" aria-label="Interview Progress" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100" id="dll_progressBar"><div class="progress-bar" style="width: 0%;"></div></div>'
);

// initial animation
var _initialPageLoad = true;

// perform the following for every page
$(document).on('daPageLoad', function () {
  let _isLastPage = false;
  // update progress bar every time we proceed through the interview
  if ($('#daquestion .progress').length > 0) {
    $('#dll_progressBar').attr(
      'aria-valuenow',
      $('#daquestion .progress').attr('aria-valuenow')
    );
    $('#dll_progressBar .progress-bar').css(
      'width',
      $('#daquestion .progress').text()
    );
    if ($('#daquestion .progress').text() == '100%') _isLastPage = true;
  } else {
    $('#dll_progressBar').attr('aria-valuenow', '0');
    $('#dll_progressBar .progress-bar').css('width', '0%');
  }

  // make question section wider
  $('#daquestion')
    .removeClass('offset-lg-3 offset-md-2 col-lg-6 col-md-8')
    .addClass('col-lg-10');
  // style the question cards (stack)
  $(
    '#daform .da-page-header, #daform .da-subquestion, #daform .da-field-container'
  ).wrapAll(
    "<div id='dll_questionCards'><div id='dll_questionCard'></div></div>"
  );
  // hide the bg when dll_noQuesitonCardBg is true
  if (typeof dll_noQuestionCardBg != 'undefined') {
    $('#dll_questionCards #dll_questionCard').addClass('dll_questionCard_noBg');
  }
  // add empty card for stack effect
  if (!_isLastPage)
    $('#dll_questionCards').append("<div id='dll_questionCard'></div>");

  // animate in questions
  setTimeout(() => {
    // make the body visible
    $('#dabody').css('content-visibility', 'visible');
    var tl = anime.timeline({
      easing: 'easeInOutSine',
    });
    // only animate logo and footer at first start up
    if (_initialPageLoad) {
      tl.add({
        targets: '#CLCSA_logo',
        opacity: [0, 1],
        translateY: [-20, 0],
        translateX: [-20, 0],
        duration: 500,
        rotate: [-25, 0],
      });
      tl.add(
        {
          targets: '#CLCSA_btns',
          opacity: [0, 1],
          scale: [0.9, 1],
          // translateY: [-20, 0],
          translateX: [40, 0],
          duration: 500,
          // rotate: [-25, 0],
        },
        '-=500'
      );
      tl.add(
        {
          targets: '#daform',
          opacity: [0, 1],
          duration: 300,
        },
        '-=300'
      );
      tl.add(
        {
          targets: '#dll_questionCards',
          scale: [0.86, 1],
          easing: 'spring(1, 80, 10, 0)',
          duration: 300,
        },
        '-=300'
      );
      // animate in buttons
      tl.add(
        {
          targets: '.da-field-buttons',
          scale: [0.95, 1],
          translateY: [12, 0],
          opacity: [0, 1],
          duration: 500,
          easing: 'spring(1, 80, 10, 0)',
        },
        '-=1300'
      );
      tl.add(
        {
          targets: 'body > footer',
          opacity: [0, 1],
          duration: 500,
        },
        '-=1350'
      );
    } else {
      // next page animation
      tl.add({
        targets: '#daform',
        opacity: [0, 1],
        duration: 2,
      });
      tl.add(
        {
          targets: '#dll_questionCards',
          scale: [0.8, 1],
          easing: 'spring(1, 100, 22, 18)',
          duration: 5,
        },
        '-=5'
      );
      // animate in buttons
      tl.add(
        {
          targets: '.da-field-buttons',
          scale: [0.95, 1],
          translateY: [12, 0],
          opacity: [0, 1],
          duration: 10,
          easing: 'spring(1, 90, 20, 17)',
        },
        '-=950'
      );
    }

    _initialPageLoad = false;
  }, 100);

  // start alpine again
  if (typeof Alpine != 'undefined') {
    Alpine.start();
  }

  // fix previous pages being displayed without bg after reaching last page
  dll_noQuestionCardBg = undefined;
});

// turn radio checkboxes into a single box selecion
function boxSelectRadio() {
  return {
    items: [],

    checkOrigin(index) {
      // get original radio element and tick
      document.querySelector('input#' + this.items[index].for).checked =
        !document.querySelector('input#' + this.items[index].for).checked;
      // a radio box allow only one item to be selected so reset
      this.items.forEach((item) => (item.checked = false));
      // update local state
      this.items[index].checked = document.querySelector(
        'input#' + this.items[index].for
      ).checked;
    },

    init() {
      // hide original radio boxes
      document.querySelector('.dafieldpart').classList.add('visually-hidden');
      let _optList = [];

      // for each checkbox item get the lable, image src, checked state, and index number
      $('.da-field-radio label').each(function (index, el) {
        console.log('element is', el);
        _optList.push({
          label: $(this).find('.labelauty-unchecked').text(),
          for: $(this).attr('for'),
          img:
            $(this).find('span.labelauty-unchecked > img')?.attr('src') ?? '',
          index: index,
          checked: $('input#' + $(this).attr('for')).is(':checked'),
        });
      });

      // update the new box list
      this.items = _optList;
    },
    replaceImgToSvg(el) {
      // DA loads svg files in img tag not svg, thus, get src and make a get request and replace img with actual svg element. this is needed to manipulate the colour when the background is dark
      $.get(
        el.src,
        function (data, status) {
          if (status == 'success') {
            let svgEl = $(data).find('svg');
            el.replaceWith(svgEl[0]);
          }
        },
        'xml'
      );
    },
  };
}

// turn checkboxes into a multi box selecion
function boxSelectMulti() {
  return {
    items: [],

    checkOrigin(index) {
      // get original checkbox item and toggle
      document.querySelector('input#' + this.items[index].for).checked =
        !document.querySelector('input#' + this.items[index].for).checked;
      // update local state
      this.items[index].checked = document.querySelector(
        'input#' + this.items[index].for
      ).checked;
    },

    init() {
      // hide original checkboxes
      document.querySelector('.dafieldpart').classList.add('visually-hidden');
      let _optList = [];

      // for each checkbox item get the lable, image src, checked state, and index number
      $('.da-field-checkboxes label').each(function (index, el) {
        console.log('element is', el);
        _optList.push({
          label: $(this).find('.labelauty-unchecked').text(),
          for: $(this).attr('for'),
          img:
            $(this).find('span.labelauty-unchecked > img')?.attr('src') ?? '',
          index: index,
          checked: $('input#' + $(this).attr('for')).is(':checked'),
        });
      });

      // update the new box list
      this.items = _optList;
    },
    replaceImgToSvg(el) {
      // DA loads svg files in img tag not svg, thus, get src and make a get request and replace img with actual svg element. this is needed to manipulate the colour when the background is dark
      $.get(
        el.src,
        function (data, status) {
          if (status == 'success') {
            let svgEl = $(data).find('svg');
            el.replaceWith(svgEl[0]);
          }
        },
        'xml'
      );
    },
  };
}

// insert Alpine into head with defer
$('head').append(
  $(
    '<script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>'
  )[0]
);
