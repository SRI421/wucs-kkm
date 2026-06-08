(function () {
  function bindDragScroll(element) {
    var isDragging = false;
    var startX = 0;
    var startY = 0;
    var scrollLeft = 0;
    var scrollTop = 0;

    element.addEventListener('mousedown', function (event) {
      if (event.button !== 0) return;
      isDragging = true;
      startX = event.pageX;
      startY = event.pageY;
      scrollLeft = element.scrollLeft;
      scrollTop = element.scrollTop;
      element.classList.add('dragscroll-active');
    });

    window.addEventListener('mouseup', function () {
      isDragging = false;
      element.classList.remove('dragscroll-active');
    });

    window.addEventListener('mousemove', function (event) {
      if (!isDragging) return;
      event.preventDefault();
      element.scrollLeft = scrollLeft - (event.pageX - startX);
      element.scrollTop = scrollTop - (event.pageY - startY);
    });
  }

  function initDragScroll() {
    document.querySelectorAll('.dragscroll').forEach(function (element) {
      if (element.dataset.dragscrollReady) return;
      element.dataset.dragscrollReady = '1';
      bindDragScroll(element);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDragScroll);
  } else {
    initDragScroll();
  }
}());
