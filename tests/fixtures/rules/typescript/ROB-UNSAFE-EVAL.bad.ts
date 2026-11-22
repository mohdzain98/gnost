function run(code) {
  // expect: ROB-UNSAFE-EVAL
  eval(code);
  // expect: ROB-UNSAFE-EVAL
  return new Function('a', code);
}
