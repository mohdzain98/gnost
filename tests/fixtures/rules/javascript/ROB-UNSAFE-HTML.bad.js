function show(el, userInput) {
  // expect: ROB-UNSAFE-HTML
  el.innerHTML = userInput;
}

function view(html) {
  // expect: ROB-UNSAFE-HTML
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}
