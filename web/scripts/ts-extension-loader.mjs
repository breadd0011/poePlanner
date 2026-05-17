export async function resolve(specifier, context, nextResolve) {
  try {
    return await nextResolve(specifier, context);
  } catch (error) {
    const shouldTryTsExtension =
      (specifier.startsWith("./") || specifier.startsWith("../")) &&
      !/\.[cm]?[jt]sx?$/.test(specifier);

    if (!shouldTryTsExtension) throw error;

    return nextResolve(`${specifier}.ts`, context);
  }
}
