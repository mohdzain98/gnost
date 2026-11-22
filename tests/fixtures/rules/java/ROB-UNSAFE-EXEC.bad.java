class Sample {
  void run(String command) throws IOException {
    // expect: ROB-UNSAFE-EXEC
    Runtime.getRuntime().exec(command);
  }
}
