class Sample {
  void work() {
    try {
      step();
    } catch (IOException e) {
      // expect: OBS-PRINT-STACKTRACE
      e.printStackTrace();
    }
  }
}
