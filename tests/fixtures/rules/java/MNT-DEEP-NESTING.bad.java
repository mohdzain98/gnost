class Sample {
  // expect: MNT-DEEP-NESTING
  int deep(boolean a, boolean b, boolean c, boolean d, boolean e) {
    if (a) {
      if (b) {
        if (c) {
          if (d) {
            if (e) {
              return 1;
            }
          }
        }
      }
    }
    return 0;
  }
}
