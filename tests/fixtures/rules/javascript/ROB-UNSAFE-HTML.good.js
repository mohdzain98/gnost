function show(el, userInput) {
  el.textContent = userInput;
  el.innerHTML = '<b>static</b>';
}

function view() {
  return <div dangerouslySetInnerHTML={{ __html: '<b>static</b>' }} />;
}
