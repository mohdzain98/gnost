function same(a, b) {
  // expect: ROB-LOOSE-EQUALITY
  if (a == b) {
    return true;
  }
  return a != b;
}
