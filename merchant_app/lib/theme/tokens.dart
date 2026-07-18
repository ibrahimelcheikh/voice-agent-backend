import 'package:flutter/material.dart';

/// AtlasPrimeX shared design tokens — kept identical to the design files
/// (README.md + the JSX `C` map). Do not drift these values.
class AppColors {
  static const bg = Color(0xFFEFE9DF);
  static const card = Color(0xFFFDFBF7);
  static const cardAlt = Color(0xFFF5F0E7);
  static const ink = Color(0xFF1B2431);
  static const sub = Color(0xFF6B7280);
  static const line = Color(0xFFEAE3D6);
  static const blue = Color(0xFF2E6BFF);
  static const blueDeep = Color(0xFF1E4FD8);
  static const blueSoft = Color(0xFFE7EEFF);
  static const green = Color(0xFF3FB27F);
  static const greenSoft = Color(0xFFE4F5EC);
  static const amber = Color(0xFFE8934A);
  static const amberSoft = Color(0xFFFBEAD9);
  static const rose = Color(0xFFE76A8B);
  static const roseSoft = Color(0xFFFBE6EC);
  static const violet = Color(0xFF7C6BE8);
  static const violetSoft = Color(0xFFECE9FC);
  static const toggleOff = Color(0xFFD8D2C6);
}

/// Soft double card shadow used across every card in the design.
const List<BoxShadow> kCardShadow = [
  BoxShadow(color: Color(0x0A1B2431), blurRadius: 2, offset: Offset(0, 1)),
  BoxShadow(color: Color(0x0D1B2431), blurRadius: 24, offset: Offset(0, 8)),
];
