function save(data) {
  try {
    write(data);
  } 
  // expect: OBS-SWALLOWED-ERROR
  catch (err) {
    count += 1;
  }
}
