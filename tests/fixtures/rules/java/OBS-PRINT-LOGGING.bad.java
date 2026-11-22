class Sample {
  void work() {
    // expect: OBS-PRINT-LOGGING
    System.out.println("start");
    System.out.printf("%s", "details");
  }
}
