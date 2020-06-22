/* this ALWAYS GENERATED file contains the definitions for the interfaces */
#ifndef __ILVTypeInterface_h__
#define __ILVTypeInterface_h__

#if defined(_WIN32) || defined(WIN32) || defined(__WIN32__) || defined(NI_DSC_WIN32)
#define NIDL_STDMETHODCALLTYPE __stdcall
#else // WIN32
#define NIDL_STDMETHODCALLTYPE
#endif // WIN32

#ifndef NIDL_EXTERN_C
#ifdef __cplusplus
#define NIDL_EXTERN_C extern "C"
#else // __cplusplus
#define NIDL_EXTERN_C
#endif // __cplusplus
#endif // NIDL_EXTERN_C

#ifndef NIDL_INTERFACE
#if defined(WIN32) || (defined(PHARLAP) && PHARLAP)
#define NIDL_INTERFACE(x) struct __declspec(uuid(x))
#else // WIN32
#define NIDL_INTERFACE(x) struct
#endif // WIN32
#endif // NIDL_INTERFACE
/* Forward Declarations */

#ifndef __ILVTypeDescriptor_FWD_DEFINED__
#define __ILVTypeDescriptor_FWD_DEFINED__
typedef struct ILVTypeDescriptor ILVTypeDescriptor;
#endif  /* __ILVTypeDescriptor_FWD_DEFINED__ */

#ifndef __ILVBooleanTypeDescriptor_FWD_DEFINED__
#define __ILVBooleanTypeDescriptor_FWD_DEFINED__
typedef struct ILVBooleanTypeDescriptor ILVBooleanTypeDescriptor;
#endif  /* __ILVBooleanTypeDescriptor_FWD_DEFINED__ */

#ifndef __ILVNumericTypeDescriptor_FWD_DEFINED__
#define __ILVNumericTypeDescriptor_FWD_DEFINED__
typedef struct ILVNumericTypeDescriptor ILVNumericTypeDescriptor;
#endif  /* __ILVNumericTypeDescriptor_FWD_DEFINED__ */

#ifndef __ILVArrayTypeDescriptor_FWD_DEFINED__
#define __ILVArrayTypeDescriptor_FWD_DEFINED__
typedef struct ILVArrayTypeDescriptor ILVArrayTypeDescriptor;
#endif  /* __ILVArrayTypeDescriptor_FWD_DEFINED__ */

#ifndef __ILVStringTypeDescriptor_FWD_DEFINED__
#define __ILVStringTypeDescriptor_FWD_DEFINED__
typedef struct ILVStringTypeDescriptor ILVStringTypeDescriptor;
#endif  /* __ILVStringTypeDescriptor_FWD_DEFINED__ */

#ifndef __ILVClusterTypeDescriptor_FWD_DEFINED__
#define __ILVClusterTypeDescriptor_FWD_DEFINED__
typedef struct ILVClusterTypeDescriptor ILVClusterTypeDescriptor;
#endif  /* __ILVClusterTypeDescriptor_FWD_DEFINED__ */


/* Header files for imported files */

#include "unknwn.h"

/* Declarations */

// ==================================================================
// NI CONFIDENTIAL													
// (c) Copyright 2006-2008 by National Instruments Corp.				
// All rights reserved.												
//																	
// @file		ILVTypeInterface.idl									
// @brief	Interface definitions for LabVIEW types.				
//			The files ILVTypeInterface_i.c and ILVTypeInterface.h	
//			are generated using this ILVTypeInterface.idl.			
// ==================================================================
#include "extcode.h"
#ifndef _fundtypes_H
typedef char int8_t;

typedef unsigned char uint8_t;

typedef short int16_t;

typedef unsigned short uint16_t;

typedef int int32_t;

typedef unsigned int uint32_t;

typedef char int8;

typedef unsigned char uInt8;

typedef uInt8 uChar;

typedef short int int16;

typedef unsigned short int uInt16;

typedef long int32;

typedef unsigned long uInt32;

typedef float float32;

typedef double float64;

typedef __int64 int64;

typedef unsigned __int64 uInt64;

typedef struct  {
   int32 mlo;
   int32 mhi;
   int16 e;
} floatExt;

typedef struct  {
   float32 re;
   float32 im;
} cmplx64;

typedef struct  {
   float64 re;
   float64 im;
} cmplx128;

typedef struct  {
   floatExt re;
   floatExt im;
} cmplxExt;

typedef int32 Bool32;

typedef __int64 int64_t;

typedef unsigned __int64 uint64_t;

typedef long HRESULT;

typedef long SCODE;

typedef unsigned int uintptr_t;

typedef unsigned char* va_list;

typedef unsigned int size_t;

typedef size_t rsize_t;

typedef int intptr_t;

typedef int ptrdiff_t;

typedef unsigned short wint_t;

typedef unsigned short wctype_t;

typedef int errcode;

typedef int errno_t;

typedef long __time32_t;

typedef __int64 __time64_t;

typedef __time64_t time_t;

typedef struct threadlocaleinfostruct {
} threadlocaleinfostruct;

typedef struct threadmbcinfostruct {
} threadmbcinfostruct;

typedef struct threadlocaleinfostruct {
}* pthreadlocinfo;

typedef struct threadmbcinfostruct {
}* pthreadmbcinfo;

typedef struct __lc_time_data {
} __lc_time_data;

typedef struct localeinfo_struct {
   pthreadlocinfo locinfo;
   pthreadmbcinfo mbcinfo;
}* _locale_t;

typedef struct localeinfo_struct {
   pthreadlocinfo locinfo;
   pthreadmbcinfo mbcinfo;
} _locale_tstruct;

typedef struct tagLC_ID {
   unsigned short wLanguage;
   unsigned short wCountry;
   unsigned short wCodePage;
}* LPLC_ID;

typedef struct tagLC_ID {
   unsigned short wLanguage;
   unsigned short wCountry;
   unsigned short wCodePage;
} LC_ID;

typedef struct threadlocaleinfostruct {
   int refcount;
   unsigned int lc_codepage;
   unsigned int lc_collate_cp;
   unsigned long lc_handle[6];
   LC_ID lc_id[6];
   struct  {
   unsigned char* locale;
   wchar_t* wlocale;
   int* refcount;
   int* wrefcount;
} lc_category[6];
   int lc_clike;
   int mb_cur_max;
   int* lconv_intl_refcount;
   int* lconv_num_refcount;
   int* lconv_mon_refcount;
   struct lconv {
}* lconv;
   int* ctype1_refcount;
   unsigned short* ctype1;
   const unsigned short* pctype;
   const unsigned char* pclmap;
   const unsigned char* pcumap;
   struct __lc_time_data {
}* lc_time_curr;
} threadlocinfo;

   virtual int* NIDL_STDMETHODCALLTYPE _errno(void) = 0;
   virtual errno_t NIDL_STDMETHODCALLTYPE _set_errno(
      int _Value) = 0;
   virtual errno_t NIDL_STDMETHODCALLTYPE _get_errno(
      int* _Value) = 0;
   virtual unsigned long NIDL_STDMETHODCALLTYPE __threadid(void) = 0;
   virtual uintptr_t NIDL_STDMETHODCALLTYPE __threadhandle(void) = 0;
typedef int32 MgErr;

#endif // ifndef _fundtypes
/* Generated header for interface ILVTypeDescriptor */

typedef enum  {
   kCompareDefaultCheck = 0,
   kCompareAllNameCheck = 1,
   kCompareSubNameCheck = 2,
   kCompareNoTypeDefCheck = 8,
} CompareWithOptionMasks;
NIDL_EXTERN_C const IID IID_ILVTypeDescriptor;

/* {09a66b9c-3683-4f5c-b4ce-b7e428fc3914} */
NIDL_INTERFACE("09a66b9c-3683-4f5c-b4ce-b7e428fc3914") ILVTypeDescriptor : public IUnknown
{
public:
   virtual MgErr NIDL_STDMETHODCALLTYPE Compare(
      ILVTypeDescriptor* type,
      int32* retVal) = 0;
   virtual MgErr NIDL_STDMETHODCALLTYPE CompareWithOptions(
      ILVTypeDescriptor* type,
      int32 compareOptions,
      int32* retVal) = 0;
   virtual MgErr NIDL_STDMETHODCALLTYPE GetTypeCode(
      int16* typeCode) = 0;
   virtual MgErr NIDL_STDMETHODCALLTYPE GetInternalLVTypeDescriptor(
      void** ppInternalTypeDesc) = 0;
} ;

/* Generated header for interface ILVBooleanTypeDescriptor */

NIDL_EXTERN_C const IID IID_ILVBooleanTypeDescriptor;

/* {234324fe-6e30-4cca-98f0-155793f2c682} */
NIDL_INTERFACE("234324fe-6e30-4cca-98f0-155793f2c682") ILVBooleanTypeDescriptor : public ILVTypeDescriptor
{
public:
} ;

/* Generated header for interface ILVNumericTypeDescriptor */

typedef enum  {
   kNonNumericInterfaceCode = 0,
   kInt8InterfaceCode = 1,
   kInt16InterfaceCode = 2,
   kInt32InterfaceCode = 3,
   kInt64InterfaceCode = 4,
   kUInt8InterfaceCode = 5,
   kUInt16InterfaceCode = 6,
   kUInt32InterfaceCode = 7,
   kUInt64InterfaceCode = 8,
   kFloat32InterfaceCode = 9,
   kFloat64InterfaceCode = 10,
   kFloatExtInterfaceCode = 11,
   kComplex64InterfaceCode = 12,
   kComplex128InterfaceCode = 13,
   kComplexExtInterfaceCode = 14,
} NumericInterfaceCode;
NIDL_EXTERN_C const IID IID_ILVNumericTypeDescriptor;

/* {da09ad59-f1b8-46b3-aba0-4b48c98a8afb} */
NIDL_INTERFACE("da09ad59-f1b8-46b3-aba0-4b48c98a8afb") ILVNumericTypeDescriptor : public ILVTypeDescriptor
{
public:
   virtual MgErr NIDL_STDMETHODCALLTYPE GetNumericCode(
      NumericInterfaceCode* numericCode) = 0;
   virtual Bool32 NIDL_STDMETHODCALLTYPE IsEnum(void) = 0;
   virtual MgErr NIDL_STDMETHODCALLTYPE GetEnumNumElements(
      uInt32* numElements) = 0;
   virtual MgErr NIDL_STDMETHODCALLTYPE GetEnumElementName(
      uInt32 position,
      const uChar** elementName,
      size_t* elementNameLength) = 0;
   virtual MgErr NIDL_STDMETHODCALLTYPE GetEnumElementNameILVString(
      uInt32 position,
      ILVString** elementName) = 0;
   virtual MgErr NIDL_STDMETHODCALLTYPE GetEnumElementNumber(
      const uChar* elementName,
      size_t elementNameLength,
      uInt32* position) = 0;
   virtual MgErr NIDL_STDMETHODCALLTYPE GetEnumElementNumberILVString(
      ILVString* elementName,
      uInt32* position) = 0;
} ;

/* Generated header for interface ILVArrayTypeDescriptor */

NIDL_EXTERN_C const IID IID_ILVArrayTypeDescriptor;

/* {c2d6f738-f5b3-4db1-a1fa-5672fdeaf60f} */
NIDL_INTERFACE("c2d6f738-f5b3-4db1-a1fa-5672fdeaf60f") ILVArrayTypeDescriptor : public ILVTypeDescriptor
{
public:
   virtual MgErr NIDL_STDMETHODCALLTYPE GetElementTypeDescriptor(
      ILVTypeDescriptor** elementTypeDescriptor) = 0;
   virtual MgErr NIDL_STDMETHODCALLTYPE GetNumDimensions(
      uInt32* numDimensions) = 0;
} ;

/* Generated header for interface ILVStringTypeDescriptor */

NIDL_EXTERN_C const IID IID_ILVStringTypeDescriptor;

/* {7b4ef86e-e843-41f4-a4d8-88a2f2372365} */
NIDL_INTERFACE("7b4ef86e-e843-41f4-a4d8-88a2f2372365") ILVStringTypeDescriptor : public ILVTypeDescriptor
{
public:
   virtual Bool32 NIDL_STDMETHODCALLTYPE IsVariableSize(void) = 0;
   virtual Bool32 NIDL_STDMETHODCALLTYPE IsBoundedSize(void) = 0;
   virtual Bool32 NIDL_STDMETHODCALLTYPE IsFixedSize(void) = 0;
   virtual MgErr NIDL_STDMETHODCALLTYPE GetCapacity(
      size_t* size) = 0;
} ;

/* Generated header for interface ILVClusterTypeDescriptor */

NIDL_EXTERN_C const IID IID_ILVClusterTypeDescriptor;

/* {fc873d27-ad8e-45da-bd26-e3f42c3d8157} */
NIDL_INTERFACE("fc873d27-ad8e-45da-bd26-e3f42c3d8157") ILVClusterTypeDescriptor : public ILVTypeDescriptor
{
public:
   virtual MgErr NIDL_STDMETHODCALLTYPE GetNumElements(
      uInt32* numElements) = 0;
   virtual MgErr NIDL_STDMETHODCALLTYPE GetNumElementsRecursive(
      uInt32* numElements) = 0;
   virtual MgErr NIDL_STDMETHODCALLTYPE GetElementTypeDescriptor(
      uInt32 position,
      ILVTypeDescriptor** elementTypeDescriptor) = 0;
   virtual MgErr NIDL_STDMETHODCALLTYPE GetElementName(
      uInt32 position,
      ILVString** name) = 0;
   virtual MgErr NIDL_STDMETHODCALLTYPE GetElementIndex(
      ILVString* name,
      int32* index) = 0;
} ;



#endif /* __ILVTypeInterface_h__ */
