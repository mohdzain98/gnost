function f(): number {
  // @ts-expect-error the value is checked at runtime
  return 'text';
}
