class Sample {
  void load() {
    try {
      risky();
    }
    // expect: ROB-EMPTY-CATCH
    catch (IOException e) {}
  }
}
