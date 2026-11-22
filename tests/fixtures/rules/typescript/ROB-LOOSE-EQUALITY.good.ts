function same(a, b) {
  if (a === b) {
    return true;
  }
  if (a == null) {
    return false;
  }
  return a !== b;
}
