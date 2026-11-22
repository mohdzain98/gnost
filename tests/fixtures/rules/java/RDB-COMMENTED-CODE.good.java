class Sample {
  void f() {
    // Runs the step. The old version computed it twice, which was slow.
    step();
  }
}
